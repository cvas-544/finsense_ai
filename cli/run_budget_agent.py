"""
Script Name: run_budget_agent.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-19
Description: CLI script to run the BudgetingAgent interactively
             with custom user input and display memory trace.
"""

from agents.budgeting_agent import create_budgeting_agent

def main():
    print("\n🔁 FinSense BudgetingAgent CLI")
    print("Type your budget-related question or task (e.g. 'categorize this month's spending').")
    print("Type 'exit' to quit.\n")

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
