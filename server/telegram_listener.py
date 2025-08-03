"""
File: telegram_listener.py
Purpose:
    Telegram listener for FinSense Agent.
    - Handles /start
    - Processes text messages and routes to the budgeting agent
    - Supports per-user budget summary via telegram_id lookup
"""

from utils.notion_sync_runner import sync_from_notion
from agents.onboarding_flow import load_user_profile
from agents.budgeting_agent import create_budgeting_agent
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from tools.budgeting_tools import (
    summarize_category_spending,
    summarize_budget,
    extract_transactions_from_db,
)
from utils.transactions_store import get_all_transactions
from utils.query_parser import call_parse_budget_query
from utils.db_connection import get_db_connection

# One-time startup
sync_from_notion()
profile = load_user_profile()
print("✅ Notion synced. Profile loaded.")

agent = create_budgeting_agent()
TELEGRAM_TOKEN = "7628731197:AAF4KW4zLyDMQWhFbC7ZKS0B8N-Rh_VoFpc"


def get_user_id_from_telegram_id(telegram_id: int) -> str:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM user_profile WHERE telegram_id = %s", (telegram_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return str(row[0]) if row else None
    except Exception as e:
        print(f"❌ Error fetching user_id: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hi! I’m FinSense. Ask me anything about your budget!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    telegram_id = update.effective_user.id
    print(f"\n📨 Message from Telegram ID {telegram_id}: {query}")

    user_id = get_user_id_from_telegram_id(telegram_id)
    if not user_id:
        await update.message.reply_text("⚠️ You are not onboarded yet. Please use the web app to create your profile.")
        return

    try:
        print("🔍 [Parser] Attempting to parse budget query…")
        parsed = call_parse_budget_query(query)
        category = parsed.get("category")
        month = parsed.get("month")
        print(f"✅ [Parser] category={category}, month={month}")

        txs = get_all_transactions()

        if "budget" in query.lower():
            print("📊 Running summarize_budget()")
            reply = summarize_budget(user_id=user_id, month=month)
        elif "income" in query.lower():
            from tools.budgeting_tools import summarize_income
            print("💰 Running summarize_income()")
            reply = summarize_income(user_id=user_id, month=month)
        else:
            print("📂 Running summarize_category_spending()")
            reply = summarize_category_spending(user_id=user_id, category=category, month=month)

    except Exception as e:
        print(f"⚠️ Fallback to agent due to error: {e}")
        result = agent.run(user_input=query, max_iterations=10)
        if hasattr(result, "get_memories"):
            messages = result.get_memories()
            assistant_msgs = [m for m in messages if m.get("type") == "assistant" and m.get("content")]
            reply = assistant_msgs[-1]["content"].strip() if assistant_msgs else "🤖 No assistant response found."
        else:
            reply = str(result).strip()

    print(f"📤 Reply: {reply}")
    await update.message.reply_text(reply)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()