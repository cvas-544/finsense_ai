"""
File: telegram_listener.py
Purpose:
    Telegram listener for FinSense Agent.
    - Handles /start
    - Processes text messages and routes to the budgeting agent
    - Uses fresh transactions before every tool call
    - Formats and returns human-friendly replies
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

# One-time startup sync
sync_from_notion()
profile = load_user_profile()
print("✅ Notion synced. Profile loaded.")

agent = create_budgeting_agent()
TELEGRAM_TOKEN = "7628731197:AAF4KW4zLyDMQWhFbC7ZKS0B8N-Rh_VoFpc"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hi! I’m FinSense. Ask me anything about your budget!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    print(f"\n📨 User asked: {query}")

    result = agent.run(user_input=query, max_iterations=10)
    print("🔍 Raw Agent Result:", result)

    reply = "✅ Done!"
    try:
        txs = get_all_transactions()

        if isinstance(result, dict) and "tool" in result:
            tool = result["tool"]
            args = result.get("args", {})

            if tool == "summarize_category_spending":
                reply = summarize_category_spending(
                category=args.get("category"),
                month=args.get("month")
                )
            elif tool == "summarize_budget":
                reply = summarize_budget(
                    transactions=txs,
                    budgets=args.get("budgets", "50/30/20"),
                    month=args.get("month")
                )
            else:
                reply = f"✅ Tool `{tool}` executed."

        elif hasattr(result, "get_memories"):
            messages = result.get_memories()
            assistant_msgs = [m for m in messages if m.get("type") == "assistant" and m.get("content")]
            if assistant_msgs:
                reply = assistant_msgs[-1]["content"].strip()
            else:
                reply = "🤖 No assistant response found."

        elif isinstance(result, str):
            reply = result.strip()

    except Exception as e:
        reply = f"❌ Error: {e}"
        print("⚠️ Exception:", e)

    print(f"📤 Reply to user: {reply}")
    await update.message.reply_text(reply)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()