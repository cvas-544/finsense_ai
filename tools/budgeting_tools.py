"""
Script Name: budgeting_tools.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-19
Description: Budgeting-related tools used by BudgetingAgent.
             Includes PDF parsing, transaction categorization,
             salary and income tracking, and 50/30/20 budgeting analysis.
"""

import pdfplumber
import re
import json
from datetime import datetime
from typing import List, Dict
from tools.shared_registry import register_tool
from typing import List, Dict, Union
from tools.shared_registry import register_tool
from memory.memory_store import Memory  # Make sure this exists in your structure

# -----------------------------------------
# 📄 Tool 1: Parse Bank Statement PDF
# -----------------------------------------

@register_tool(tags=["budgeting"])
def parse_bank_pdf(file_path: str) -> List[Dict]:
    """
    Parses a bank statement PDF and extracts transactions.
    Returns a list of dicts with 'date', 'amount', 'description'.
    
    Args:
        file_path: The local path to the PDF file
    
    Returns:
        A list of transactions in structured format
    """
    transactions = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split("\n")
            for line in lines:
                # Very basic matching, customize as per your PDF format
                match = re.match(r"(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+(-?\d+,\d{2}) €", line)
                if match:
                    date_str, desc, amount_str = match.groups()
                    try:
                        amount = float(amount_str.replace(".", "").replace(",", "."))
                        date = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                        transactions.append({
                            "date": date,
                            "amount": amount,
                            "description": desc.strip()
                        })
                    except Exception:
                        continue  # skip malformed lines
    return transactions


# -----------------------------------------
# 💳 Tool 2: Categorize Transactions
# -----------------------------------------

@register_tool(tags=["budgeting"])
def categorize_transactions(transactions: List[Dict]) -> List[Dict]:
    """
    Categorizes each transaction into 'needs', 'wants', or 'savings'
    based on simple rule matching in description.
    """
    # ✅ If input is a string, parse it into a list
    if isinstance(transactions, str):
        try:
            transactions = json.loads(transactions)
        except json.JSONDecodeError:
            raise ValueError("Failed to parse transaction JSON string.")

    categorized = []
    for tx in transactions:
        desc = tx["description"].lower()
        category = "other"

        if any(k in desc for k in ["rewe", "edeka", "aldi", "dm", "apotheke", "emi", "loan", "rent"]):
            category = "needs"
        elif any(k in desc for k in ["netflix", "spotify", "starbucks", "eating", "uber"]):
            category = "wants"
        elif tx["amount"] > 0:
            category = "savings"

        tx["category"] = category
        categorized.append(tx)

    return categorized


# -----------------------------------------
# 📊 Tool 3: Summarize Budget Based on 50/30/20 Rule
# -----------------------------------------

@register_tool(tags=["budgeting"])
def summarize_budget(transactions: List[Dict], income: float) -> Dict:
    """
    Summarizes the current month's budget against the 50/30/20 rule.
    
    Args:
        transactions: Categorized transactions
        income: User-defined monthly income
    
    Returns:
        Dictionary summary with actuals vs limits
    """
    spent = {"needs": 0, "wants": 0, "savings": 0}
    for tx in transactions:
        cat = tx.get("category")
        amt = abs(tx["amount"])
        if cat in spent:
            spent[cat] += amt

    limits = {
        "needs": round(income * 0.50, 2),
        "wants": round(income * 0.30, 2),
        "savings": round(income * 0.20, 2)
    }

    summary = {
        "actual_spending": spent,
        "budget_limits": limits,
        "over_budget": {
            k: spent[k] - limits[k]
            for k in spent if spent[k] > limits[k]
        }
    }

    return summary


# -----------------------------------------
# 💼 Tool 4: Record Base Salary
# -----------------------------------------

@register_tool(tags=["budgeting"])
def record_income(amount: float) -> str:
    """
    Records the user's monthly income for budget calculation.
    
    Args:
        amount: Monthly income in euros or rupees
    
    Returns:
        Confirmation message
    """
    try:
        with open("data/user_income.json", "w") as f:
            json.dump({"income": round(amount, 2)}, f, indent=2)
        return f"Income of €{amount:.2f} recorded successfully."
    except Exception as e:
        return f"Failed to record income: {str(e)}"


# -----------------------------------------
# 🧾 Tool 5: Record a New Income Source
# -----------------------------------------

@register_tool(tags=["budgeting"])
def record_income_source(source_name: str, amount: float) -> str:
    """
    Adds a new income source with the amount provided.
    Stores all sources in a JSON file.

    Args:
        source_name: Name of the income source (e.g., 'freelance', 'rental')
        amount: Amount received from this source

    Returns:
        Confirmation message
    """
    try:
        income_entry = {
            "source": source_name,
            "amount": round(amount, 2)
        }

        try:
            with open("data/income_sources.json", "r") as f:
                income_list = json.load(f)
        except FileNotFoundError:
            income_list = []

        income_list.append(income_entry)

        with open("data/income_sources.json", "w") as f:
            json.dump(income_list, f, indent=2)

        return f"Income source '{source_name}' of €{amount:.2f} recorded successfully."
    except Exception as e:
        return f"Error recording income source: {str(e)}"


# -----------------------------------------
# 📈 Tool 6: Summarize All Income Sources
# -----------------------------------------

@register_tool(tags=["budgeting"])
def summarize_income() -> Dict:
    """
    Combines base salary and all income sources.
    Returns:
        A dictionary with total income and breakdown by source.
    """
    sources = []

    # 1. Load base salary from user_income.json
    try:
        with open("data/user_income.json", "r") as f:
            salary_data = json.load(f)
            salary_amount = salary_data.get("income", 0)
            if salary_amount > 0:
                sources.append({"source": "salary", "amount": salary_amount})
    except FileNotFoundError:
        salary_amount = 0

    # 2. Load extra income sources from income_sources.json
    try:
        with open("data/income_sources.json", "r") as f:
            other_sources = json.load(f)
            sources.extend(other_sources)
    except FileNotFoundError:
        pass

    # 3. Compute total income
    total = sum(entry["amount"] for entry in sources)

    return {
        "total_income": round(total, 2),
        "sources": sources,
        "message": f"Total income: €{round(total, 2)}"
    }

# -----------------------------------------
# 💡 Tool 7: Fuzzy Match from Memory
# -----------------------------------------

def fuzzy_match_transaction(memory_entries, query: str) -> List[Dict]:
    """
    Searches memory for a transaction that matches the natural language query.
    Matches against description keywords or numeric amount values.
    """
    for entry in reversed(memory_entries):
        if entry["type"] != "environment":
            continue

        content = entry.get("content")
        try:
            result = json.loads(content) if isinstance(content, str) else content
            tx = result.get("transaction") or result.get("result", {}).get("transaction")

            if not tx:
                continue

            desc = tx.get("description", "").lower()
            amt = str(tx.get("amount"))

            # Match by keyword or amount
            if query.lower() in desc or re.search(rf"\b{amt}\b", query):
                return [tx]
        except Exception:
            continue

    return []  # nothing matched


# -----------------------------------------
# 📊 Tool 8: Categorize_transactions Tool
# -----------------------------------------

@register_tool(tags=["budgeting"])
def categorize_transactions(transactions: Union[str, List[Dict]]) -> List[Dict]:
    """
    Categorizes each transaction into 'needs', 'wants', or 'savings'.
    Supports:
    - Direct transaction list
    - Fuzzy string queries like 'EMI', 'previous', or 'wifi'
    """

    if isinstance(transactions, str):
        # 1. Try parsing it as JSON string
        try:
            transactions = json.loads(transactions)
        except json.JSONDecodeError:
            # 2. Fallback to fuzzy match from memory
            memory = Memory()
            transactions = fuzzy_match_transaction(memory.get_memories(), transactions)

            if not transactions:
                raise ValueError("No matching transaction found in memory.")

    categorized = []
    for tx in transactions:
        desc = tx["description"].lower()
        category = "other"

        if any(k in desc for k in ["rewe", "edeka", "aldi", "dm", "apotheke", "emi", "loan", "rent", "wifi", "internet"]):
            category = "needs"
        elif any(k in desc for k in ["netflix", "spotify", "starbucks", "eating", "uber"]):
            category = "wants"
        elif tx["amount"] > 0:
            category = "savings"

        tx["category"] = category
        categorized.append(tx)

    return categorized


# -----------------------------------------
# 📈 Tool Terminate: Agent Terminate
# -----------------------------------------

@register_tool(tags=["budgeting"], terminal=True)
def terminate(message: str) -> str:
    """
    A fallback tool when the agent doesn't recognize the task.
    Returns the message as a reason for stopping.
    """
    return f"Agent terminated: {message}"
