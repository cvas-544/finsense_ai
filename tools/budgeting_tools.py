"""
Script Name: budgeting_tools.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-20
Description: Cleaned and enhanced version of budgeting tools module.
"""

import pdfplumber
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Union, Optional
from tools.shared_registry import register_tool
from memory.memory_store import Memory


# ----------------------------
# Tool: 🧠 Fuzzy Match Helper
# ----------------------------

def fuzzy_match_transaction_db(query: str) -> Optional[Dict]:
    try:
        with open("data/transactions.json", "r") as f:
            transactions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    for tx in reversed(transactions):
        desc = tx.get("description", "").lower()
        amt = str(tx.get("amount"))

        if query.lower() in desc or query.strip() == amt:
            return tx
    return None

# ----------------------------
# Tool: 🔁 Extract from Memory Helper
# ----------------------------

def extract_transactions_from_db() -> List[Dict]:
    """
    Loads all categorized transactions from the persistent JSON database.

    Returns:
        A list of transactions with both 'category' and 'type' fields.
    """
    try:
        with open("data/transactions.json", "r") as f:
            transactions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    return [
        tx for tx in transactions
        if isinstance(tx, dict) and "category" in tx and "type" in tx
    ]

# ----------------------------
# 📄 Tool: Parse Bank PDF
# ----------------------------

@register_tool(tags=["budgeting"])
def parse_bank_pdf(file_path: str) -> List[Dict]:
    transactions = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split("\n")
            for line in lines:
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
                        continue
    return transactions

# -----------------------------------------
# 🧾 Tool: Record a New Income Source
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
# 💼 Tool: Record Base Salary
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

# ----------------------------
# 💳 Tool: Record Transaction
# ----------------------------

@register_tool(tags=["budgeting"])
def record_transaction(date: str, amount: float, description: str, category: str = "uncategorized") -> Dict:
    from datetime import datetime, timedelta
    import os
    import json

    # Normalize date
    date = date.lower().strip()
    if date == "today":
        date = datetime.now().strftime("%Y-%m-%d")
    elif date == "yesterday":
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: '{date}'.")

    # Load category → type mapping
    try:
        with open("data/category_type_mapping.json", "r") as f:
            mapping = json.load(f)
    except FileNotFoundError:
        mapping = {}

    category_normalized = category.strip().title()
    type_ = mapping.get(category_normalized, "uncategorized")

    if type_ == "uncategorized":
        print(f"⚠️ Warning: No type found for category '{category_normalized}'.")

    # Create transaction object
    transaction = {
        "id": f"txn_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "date": date,
        "amount": float(amount),
        "description": description,
        "category": category_normalized,
        "type": type_
    }

    # Save to global transaction DB
    os.makedirs("data", exist_ok=True)
    try:
         with open("data/transactions.json", "r") as f:
            content = f.read().strip()
            existing = json.loads(content) if content else []
    except FileNotFoundError:
        existing = []

    existing.append(transaction)

    with open("data/transactions.json", "w") as f:
        json.dump(existing, f, indent=2)

    return {
        "message": f"Transaction recorded under {category_normalized} ({type_}).",
        "transaction": transaction
    }

# ----------------------------
# 🧾 Tool: Categorize Transactions
# ----------------------------

@register_tool(tags=["budgeting"])
def categorize_transactions(transactions: Union[str, List[Dict]]) -> List[Dict]:
    # Support fuzzy string query
    if isinstance(transactions, str):
        match = fuzzy_match_transaction_db(transactions)
        if match:
            transactions = [match]
        else:
            raise ValueError("No matching transaction found in database.")

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

# ----------------------------
# 📊 Tool: Summarize Budget
# ----------------------------
@register_tool(tags=["budgeting"])
def summarize_budget() -> Dict:
    """
    Summarizes the user's spending against the 50/30/20 budget rule.
    Loads transactions and income from persistent storage.
    """
    try:
        with open("data/transactions.json", "r") as f:
            transactions = json.load(f)
    except FileNotFoundError:
        return {"message": "No transactions database found."}
    except json.JSONDecodeError:
        return {"message": "Transactions database is corrupted."}

    # 🔍 Filter only valid categorized transactions
    categorized_transactions = [
        tx for tx in transactions
        if tx.get("type", "").lower() in {"needs", "wants", "savings"}
    ]

    if not categorized_transactions:
        return {"message": "No categorized transactions found in database."}

    # 💰 Load income data
    total_income = 0.0
    sources = []

    try:
        with open("data/user_income.json", "r") as f:
            salary_data = json.load(f)
            income = salary_data.get("income", 0)
            if income:
                total_income += income
                sources.append({"source": "salary", "amount": income})
    except FileNotFoundError:
        pass

    try:
        with open("data/income_sources.json", "r") as f:
            extras = json.load(f)
            total_income += sum(x["amount"] for x in extras)
            sources.extend(extras)
    except FileNotFoundError:
        pass

    if total_income == 0:
        return {"message": "No income found to base the budget on."}

    # 🎯 Apply 50/30/20 rule
    limits = {
        "needs": round(total_income * 0.50, 2),
        "wants": round(total_income * 0.30, 2),
        "savings": round(total_income * 0.20, 2)
    }

    spent = {"needs": 0, "wants": 0, "savings": 0}
    for tx in categorized_transactions:
        cat = tx.get("type", "").lower()
        amt = abs(tx.get("amount", 0))
        if cat in spent:
            spent[cat] += amt

    over_budget = {
        k: round(spent[k] - limits[k], 2)
        for k in spent if spent[k] > limits[k]
    }

    under_budget = {
        k: round(limits[k] - spent[k], 2)
        for k in spent if spent[k] <= limits[k]
    }

    return {
        "income_sources": sources,
        "total_income": round(total_income, 2),
        "budget_limits": limits,
        "actual_spending": spent,
        "over_budget": over_budget,
        "under_budget": under_budget,
        "message": "Budget summary calculated from persistent transaction database."
    }

# -------------------------------
# 📊 Tool: Summarize Incomes
# -------------------------------

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


# ----------------------------
# 📊 Tool: Update transactions
# ----------------------------

@register_tool(tags=["budgeting"])
def update_transaction(
    transaction_match: str,
    new_description: Optional[str] = None,
    new_amount: Optional[Union[float, str]] = None,
    new_date: Optional[str] = None,
    new_category: Optional[str] = None,
    new_type: Optional[str] = None
) -> str:
    """
    Updates a transaction in the database based on a description match.

    Args:
        transaction_match: Partial string to match description
        new_description: New merchant or label
        new_amount: Updated amount
        new_date: Updated date (YYYY-MM-DD or 'today', 'yesterday')
        new_category: Updated fine-grained category
        new_type: Updated budgeting type (Needs/Wants/Savings)

    Returns:
        Confirmation message or error
    """
   # Load existing transactions
    try:
        with open("data/transactions.json", "r") as f:
            transactions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return f"No transaction database found."

    updated = False
    for tx in transactions:
        if transaction_match.lower() in tx.get("description", "").lower():
            if new_description:
                tx["description"] = new_description
            if new_amount:
                try:
                    tx["amount"] = float(new_amount)
                except ValueError:
                    return "Invalid amount format."
            if new_date:
                if new_date == "today":
                    tx["date"] = datetime.now().strftime("%Y-%m-%d")
                elif new_date == "yesterday":
                    tx["date"] = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                else:
                    tx["date"] = new_date
            if new_category:
                tx["category"] = new_category.title()
            if new_type:
                tx["type"] = new_type.title()

            # ✅ Always refresh 'type' from the final category, no matter what
            try:
                with open("data/category_type_mapping.json", "r") as f:
                    mapping = json.load(f)
                tx["type"] = mapping.get(tx.get("category", ""), "uncategorized")
                print("🔁 FINAL type mapping for", tx["category"], "→", tx["type"])
            except FileNotFoundError:
                tx["type"] = "uncategorized"

            updated = True
            break

    if not updated:
        return f"No matching transaction found for '{transaction_match}'."

    with open("data/transactions.json", "w") as f:
        json.dump(transactions, f, indent=2)

    return f"Transaction matching '{transaction_match}' updated."

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