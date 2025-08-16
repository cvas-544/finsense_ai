# server/telegram_listener.py
"""
Telegram listener for FinSense Agent.
- Loads secrets from .env
- Handles /start
- Routes free-text to parser → summary tools
- Falls back to the agent if parsing fails
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from utils.db_connection import get_db_connection
from utils.query_parser import call_parse_budget_query
from utils.transactions_store import get_all_transactions

from tools.budgeting_tools import (
    summarize_budget,
    summarize_category_spending,
    summarize_income,
)

from agents.budgeting_agent import create_budgeting_agent

# ── bootstrap ──────────────────────────────────────────────────────────────────
load_dotenv()  # <— load TELEGRAM_TOKEN and DB creds from .env

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("telegram_listener")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN environment variable is not set.")

agent = create_budgeting_agent()
log.info("🤖 Budgeting agent initialized.")


def get_user_id_from_telegram_id(telegram_id: int) -> str | None:
    """Look up our internal user_id using the Telegram user id."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM user_profile WHERE telegram_id = %s",
            (telegram_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return str(row[0]) if row else None
    except Exception as e:
        log.exception("Error fetching user_id for telegram_id=%s", telegram_id)
        return None


# ── handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I’m FinSense.\n"
        "Try: “groceries in July”, “budget July 2025”, or “income summary”."
    )


def _safe_month(month: str | None) -> str:
    """Default to current YYYY-MM if parser didn’t find one."""
    return month if month else datetime.utcnow().strftime("%Y-%m")


def _safe_category(cat: str | None) -> str:
    """Default to 'All' if parser didn’t find a category."""
    return cat if cat else "All"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text or ""
    telegram_id = update.effective_user.id
    log.info("📨 From %s: %s", telegram_id, query)

    user_id = get_user_id_from_telegram_id(telegram_id)
    if not user_id:
        await update.message.reply_text(
            "⚠️ I don’t recognize you yet. Please complete onboarding in the app."
        )
        return

    try:
        # Parse intent
        parsed = call_parse_budget_query(query)
        month = _safe_month(parsed.get("month"))
        category = _safe_category(parsed.get("category"))

        # Touch transactions store (warmup/readiness)
        try:
            _ = get_all_transactions()
        except Exception:
            # Non-fatal for summaries
            pass

        lower = query.lower()
        if "income" in lower:
            log.info("💰 summarize_income(user=%s)", user_id)
            inc = summarize_income(user_id=user_id)
            # summarize_income returns a dict; show a friendly line
            msg = inc.get("message") or f"Total income: €{inc.get('total_income', 0)}"
        elif "budget" in lower:
            log.info("📊 summarize_budget(user=%s, month=%s)", user_id, month)
            msg = summarize_budget(user_id=user_id, month=month)
        else:
            log.info(
                "📂 summarize_category_spending(user=%s, month=%s, category=%s)",
                user_id, month, category
            )
            msg = summarize_category_spending(
                user_id=user_id, month=month, category=category
            )

    except Exception as e:
        log.warning("Parser/summary failed, falling back to agent: %s", e)
        # Fallback to LLM agent
        result = agent.run(user_input=query, max_iterations=10)
        # Try to unwrap a clean assistant message if available
        msg = str(result).strip()
        try:
            if hasattr(result, "get_memories"):
                messages = result.get_memories()
                assistant_msgs = [
                    m for m in messages
                    if m.get("type") == "assistant" and m.get("content")
                ]
                if assistant_msgs:
                    msg = assistant_msgs[-1]["content"].strip()
        except Exception:
            pass

    log.info("📤 Replying: %s", msg)
    await update.message.reply_text(msg)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("🚀 Telegram bot started. Listening…")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()