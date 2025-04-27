"""
File: run_budget_agent.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-28
Description:
    CLI script to run the FinSense BudgetingAgent interactively.
    - Starts agent
    - Handles onboarding user profile if missing
    - Syncs from Notion automatically at startup
"""

from agents.budgeting_agent import create_budgeting_agent
from utils.notion_sync_runner import sync_from_notion
from agents.onboarding_flow import load_user_profile, onboarding_conversation
import os

def main():
    print("\n🔁 FinSense BudgetingAgent CLI")
    print("Type your budget-related question or task (e.g. 'categorize this month's spending').")
    print("Type 'exit' to quit.\n")

    # ✅ 1. Sync from Notion before anything
    try:
        print("🔄 Syncing from Notion before starting...")
        sync_from_notion()
        print("✅ Notion sync complete.\n")
    except Exception as e:
        print(f"⚠️ Notion sync failed: {e}")
        print("You can continue using the agent without synced data.\n")

    # ✅ 2. Check for user profile
    profile = load_user_profile()
    if not profile:
        print("\n👤 No user profile found. Let's set it up first!\n")
        onboarding_conversation()
        profile = load_user_profile()

    # ✅ 2.5 After onboarding, show a full profile summary
    print("\n📋 Here's your current profile summary:")
    print(f"   - Salary: €{profile.get('salary', 'N/A')}")
    print(f"   - Rent: €{profile.get('rent', 'N/A')}")
    print(f"   - Internet Bill: €{profile.get('internet', 'N/A')}")
    print(f"   - Electricity Bill: €{profile.get('electricity', 'N/A')}")

    fixed_costs_total = 0
    fixed_costs_total += float(profile.get('rent', 0) or 0)
    fixed_costs_total += float(profile.get('internet', 0) or 0)
    fixed_costs_total += float(profile.get('electricity', 0) or 0)

    if profile.get('other_fixed_costs'):
        print("   - Other Fixed Costs:")
        for cost in profile['other_fixed_costs']:
            print(f"     • {cost['description']}: €{cost['amount']}")
            fixed_costs_total += float(cost['amount'])
    else:
        print("   - No other fixed costs listed yet.")

    print(f"\n💶 Total Fixed Costs per Month: €{fixed_costs_total:.2f}")
    print("\n✅ Profile loaded! Starting agent...\n")

    # ✅ 3. Create the budgeting agent
    agent = create_budgeting_agent()

    # ✅ 4. CLI loop
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