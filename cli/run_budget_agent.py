"""
File: run_budget_agent.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-05-01
Description:
    CLI script to run the FinSense BudgetingAgent interactively.
    - Starts agent
    - Handles onboarding user profile if missing
    - Syncs from Notion automatically at startup
    - Routes budget queries through LLM parser + direct summarizer
"""
import os
from agents.budgeting_agent import create_budgeting_agent
from utils.notion_sync_runner import sync_from_notion
from agents.onboarding_flow import load_user_profile, onboarding_conversation
from utils.query_parser import call_parse_budget_query
from tools.budgeting_tools import (
    extract_transactions_from_db,
    summarize_category_spending,
    summarize_budget,
    summarize_income,
)


def print_memory_and_continue(memory):
    print("\n🧠 Agent Memory Log:")
    for item in memory.get_memories():
        role = item.get("type", "").upper()
        content = item.get("content", "")
        print(f"\n--- {role} ---\n{content}")
    print("\n✅ End of Run\n")


def main():
    print("\n🔁 FinSense BudgetingAgent CLI")
    print("Type your budget-related question or task (e.g. 'categorize this month's spending').")
    print("Type 'exit' to quit.\n")

    try:
        print("🔄 Syncing from Notion before starting...")
        sync_from_notion()
        print("✅ Notion sync complete.\n")
    except Exception as e:
        print(f"⚠️ Notion sync failed: {e}")
        print("You can continue using the agent without synced data.\n")

    profile = load_user_profile()
    if not profile:
        print("\n👤 No user profile found. Let's set it up first!\n")
        onboarding_conversation()
        profile = load_user_profile()

    print("\n📋 Here's your current profile summary:")
    print(f"   - Salary: €{profile.get('salary', 'N/A')}")
    print(f"   - Rent: €{profile.get('rent', 'N/A')}")
    print(f"   - Internet Bill: €{profile.get('internet', 'N/A')}")
    print(f"   - Electricity Bill: €{profile.get('electricity', 'N/A')}")
    fixed_costs_total = sum(float(profile.get(k, 0) or 0) for k in ['rent', 'internet', 'electricity'])
    if profile.get('other_fixed_costs'):
        print("   - Other Fixed Costs:")
        for cost in profile['other_fixed_costs']:
            print(f"     • {cost['description']}: €{cost['amount']}")
            fixed_costs_total += float(cost['amount'])
    else:
        print("   - No other fixed costs listed yet.")
    print(f"\n💶 Total Fixed Costs per Month: €{fixed_costs_total:.2f}")
    print("\n✅ Profile loaded! Starting agent...\n")

    agent = create_budgeting_agent()

    while True:
        user_input = input("🧾 Your input → ")
        if not user_input or user_input.lower() in ["exit", "quit"]:
            break

        try:
            print("🔍 [Parser] Attempting to parse budget query…")
            parsed = call_parse_budget_query(user_input)
            category = parsed.get("category")
            month = parsed.get("month")
            print(f"✅ [Parser] Hit: category={category!r}, month={month!r}")

            # INTENT OVERRIDE BASED ON USER INPUT
            if "income" in user_input.lower():
                print("📊 Summarizing income...")
                summary = summarize_income()
                print(f"\n🗒️ Result → {summary['message']}\n")
                continue

            if "budget" in user_input.lower():
                print("📊 Summarizing full budget...")
                summary = summarize_budget()
                if isinstance(summary, str):
                    print(f"\n🗒️ Result → {summary}\n")
                else:
                    limits = summary.get("budget_limits", {})
                    spending = summary.get("actual_spending", {})
                    print("\n🗒️ Budget Summary (50/30/20 Rule):")
                    for t in ["needs", "wants", "savings"]:
                        limit = limits.get(t, 0)
                        spent = spending.get(t, 0)
                        print(f"   - {t.title()}: Spent €{spent:.2f} of Limit €{limit:.2f}")
                    print(f"\n💬 {summary.get('message')}\n")
                continue

            # Default → category spending
            txs = extract_transactions_from_db()
            summary = summarize_category_spending(txs, month, category)
            print(f"\n🗒️ Result → {summary}\n")
            continue

        except Exception as e:
            print(f"⚠️ [Parser] No parse ({e.__class__.__name__}); falling back to agent.")
            memory = agent.run(user_input=user_input, max_iterations=10)
            print_memory_and_continue(memory)
            continue


if __name__ == "__main__":
    main()