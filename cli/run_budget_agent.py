"""
Script Name: run_budget_agent.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-22
Description: CLI script to run the BudgetingAgent interactively.
             Automatically syncs from Notion before launching.
"""

from agents.budgeting_agent import create_budgeting_agent
from utils.notion_sync_runner import sync_from_notion
import os

def main():
    print("🔁 FinSense BudgetingAgent CLI")
    print("Type your budget-related question or task (e.g. 'categorize this month's spending').")
    print("Type 'exit' to quit.\n")

    print("🔄 Syncing from Notion before starting...")
    try:
        sync_from_notion()
        print("✅ Notion sync complete.\n")
    except Exception as e:
        print(f"⚠️ Notion sync failed: {e}")
        print("You can continue using the agent without synced data.\n")

    agent = create_budgeting_agent()

    while True:
        user_input = input("🧾 Your input → ")

        if user_input.lower() in ["exit", "quit"]:
            break

        memory = agent.run(user_input=user_input, max_iterations=10)

        print("\n🧠 Agent Memory Log:")
        for item in memory.get_memories():
            role = item["type"].upper()
            content = item["content"]
            print(f"\n--- {role} ---\n{content}")

        print("\n✅ End of Run\n")

if __name__ == "__main__":
    main()
