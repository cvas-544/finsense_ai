"""
Script Name: budgeting_goals.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-19
Description: Defines budgeting-related goals for the BudgetingAgent
             to enforce monthly discipline and guide user actions.
"""

from agents.base import Goal

def get_budgeting_goals():
    """
    Returns a list of predefined budgeting goals for the agent.
    These drive the agent's intent during the reasoning loop.
    """
    return [
        Goal(
            priority=1,
            name="Track and analyze monthly spending",
            description="Extract transactions from bank PDFs and Notion to create a structured view of spending activity."
        ),
        Goal(
            priority=2,
            name="Apply 50/30/20 budgeting rule",
            description="Evaluate current month spending against the standard rule of 50% needs, 30% wants, 20% savings."
        ),
        Goal(
            priority=3,
            name="Detect over-budget categories",
            description="Warn the user if spending exceeds limits in Needs, Wants, or Savings buckets."
        ),
        Goal(
            priority=4,
            name="Summarize budget health",
            description="Present a clean summary of categorized spending and highlight savings potential."
        ),
        Goal(
            priority=5,
            name="Assist in goal-based planning",
            description="If user expresses an intent like buying shoes or saving money, help recommend changes to achieve it."
        )
    ]
