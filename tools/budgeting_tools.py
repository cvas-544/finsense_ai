"""
Script Name: budgeting_tools.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-20
Description: Cleaned and enhanced version of budgeting tools module.
"""

import re
import os
import json
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict, Union, Optional
from tools.shared_registry import register_tool
from memory.memory_store import Memory
from utils.date_helpers import extract_month_from_phrase

# Initializes the OpenAI client using the API key from environment variables.
load_dotenv()
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    import pdfplumber
    import re
    from datetime import datetime

    transactions = []
    current_date = None
    current_amount = None
    current_desc = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().splitlines()

            for line in lines:
                # Match a line starting with a date and ending with € amount
                match = re.match(r"^(\d{2}\.\d{2}\.\d{4}) (.+?) (-?\d+,\d{2}) €?$", line)
                if match:
                    date_str, desc, amount_str = match.groups()
                    try:
                        date = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                        amount = float(amount_str.replace(".", "").replace(",", "."))
                        transactions.append({
                            "date": date,
                            "amount": amount,
                            "description": desc.strip()
                        })
                    except Exception as e:
                        print(f"⚠️ Parsing error: {e}")
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

@register_tool(tags=["budgeting","manual_categorization", "label_transaction"])
def categorize_transactions(transactions: Union[str, List[Dict]]) -> List[Dict]:
    """
    Categorizes a specific transaction or list of transactions into budgeting types (Needs/Wants/Savings).
    Use when the user wants to tag a single transaction, like 'Categorize edeka' or 'Label this list'.
    """

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
    Updates details of an existing transaction already stored in the database.

    This tool is intended for user-initiated edits to transaction fields like amount, description, category, or date.
    It should be used when the user clearly wants to modify something (e.g., "Change Edeka to 50€" or "Update March rent to Housing").

    ⚠️ Do NOT use this tool for initial classification or fuzzy guessing.
    For categorization purposes, use `categorize_transactions()` or `auto_categorize_transactions()` instead.

    Args:
        transaction_match: Partial string to match the existing transaction's description.
        new_description: New merchant or label (optional).
        new_amount: Updated amount (optional).
        new_date: Updated date (e.g. 'today', 'yesterday', or YYYY-MM-DD).
        new_category: Updated fine-grained category (e.g. 'Groceries').
        new_type: Explicit budgeting type if provided (e.g. 'Needs').

    Returns:
        A confirmation message if updated, or a friendly error if not found.
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
# 📥 Tool: Import and Store PDF Transactions
# -----------------------------------------

@register_tool(tags=["budgeting"])
def import_pdf_transactions(file_path: str) -> Dict:
    """
    Parses a PDF bank statement and stores categorized transactions in the database.
    Also saves raw dump and metadata.
    """
    # ---------------------------
    # 🧾 1. Parse Transactions
    # ---------------------------
    transactions = []
    raw_transactions = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().splitlines()
            for line in lines:
                match = re.match(r"^(\d{2}\.\d{2}\.\d{4}) (.+?) (-?\d+,\d{2}) €?$", line)
                if match:
                    date_str, desc, amount_str = match.groups()
                    try:
                        date = datetime.strptime(date_str, "%d.%m.%Y")
                        iso_date = date.strftime("%Y-%m-%d")
                        month_tag = date.strftime("%Y-%m")
                        amount = float(amount_str.replace(".", "").replace(",", "."))
                        raw_tx = {
                            "date": iso_date,
                            "amount": amount,
                            "description": desc.strip()
                        }
                        raw_transactions.append(raw_tx)

                        # 🧠 Categorization
                        description_lower = desc.lower()
                        category = "Other"
                        type_ = "uncategorized"

                        if any(k in description_lower for k in ["rewe", "edeka", "aldi", "dm", "apotheke", "rent", "drillisch"]):
                            category = "Groceries"
                            type_ = "Needs"
                        elif any(k in description_lower for k in ["netflix", "spotify", "starbucks", "eating", "uber"]):
                            category = "Entertainment"
                            type_ = "Wants"
                        elif amount > 0:
                            category = "Income"
                            type_ = "Savings"

                        transactions.append({
                            "id": f"txn_{date.strftime('%Y%m%d%H%M%S')}_{len(transactions)}",
                            "date": iso_date,
                            "amount": amount,
                            "description": desc.strip(),
                            "category": category,
                            "type": type_,
                            "month": month_tag,
                            "source": os.path.basename(file_path)
                        })

                    except Exception as e:
                        print("⚠️ Failed to parse line:", line)

    # ---------------------------
    # 🧾 2. Save Raw Dump
    # ---------------------------
    raw_dir = "parsed_pdfs/raw"
    os.makedirs(raw_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    base_name = os.path.basename(file_path).replace(".pdf", "").replace(" ", "_")
    raw_path = os.path.join(raw_dir, f"{base_name}_{ts}.json")

    with open(raw_path, "w") as f:
        json.dump(raw_transactions, f, indent=2)

    # ---------------------------
    # 🧠 3. Dedup & Store to DB
    # ---------------------------
    db_path = "data/transactions.json"
    os.makedirs("data", exist_ok=True)
    try:
        with open(db_path, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    def is_duplicate(new_tx):
        return any(
            tx["date"] == new_tx["date"] and
            tx["amount"] == new_tx["amount"] and
            tx["description"] == new_tx["description"]
            for tx in existing
        )

    new_txs = [tx for tx in transactions if not is_duplicate(tx)]
    existing.extend(new_txs)

    with open(db_path, "w") as f:
        json.dump(existing, f, indent=2)

    # ---------------------------
    # 🧠 4. Save Metadata
    # ---------------------------
    meta_path = "parsed_pdfs/metadata.json"
    os.makedirs("parsed_pdfs", exist_ok=True)
    try:
        with open(meta_path, "r") as f:
            metadata = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        metadata = {}

    metadata[base_name] = {
        "parsed_at": datetime.now().isoformat(),
        "num_transactions": len(transactions),
        "raw_file": raw_path
    }

    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # ---------------------------
    # ✅ Done
    # ---------------------------
    return {
        "message": f"Imported {len(transactions)} transactions from PDF.",
        "stored": len(new_txs),
        "duplicates_skipped": len(transactions) - len(new_txs),
        "raw_dump": raw_path
    }

# -----------------------------------------
# 🧾 Tool: Auto Categorize the transactions
# -----------------------------------------

@register_tool(tags=["budgeting", "autocategorize", "auto", "clean_uncategorized", "smart_categorization"])
def auto_categorize_transactions() -> Dict:
    """
    Auto-categorizes all transactions with type 'uncategorized'.
    First attempts keyword matching. If that fails, uses LLM to guess category.
    Prompts user before applying changes.
    """
    db_path = "data/transactions.json"
    try:
        with open(db_path, "r") as f:
            transactions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"message": "No transaction database found."}

    try:
        with open("data/category_type_mapping.json", "r") as f:
            category_map = json.load(f)
    except FileNotFoundError:
        category_map = {}

    updated = []
    skipped = []

    for tx in transactions:
        if tx.get("type") == "uncategorized":
            desc = tx["description"].lower()

            # Step 1: Keyword Rule Matching
            keyword_map = {
                "groceries": ["rewe", "edeka", "aldi", "dm", "apotheke", "drillisch"],
                "subscriptions": ["netflix", "spotify", "vodafone", "pyur"],
                "commute": ["db vertrieb", "flixbus", "bahn"],
                "debt": ["klarna", "advanzia", "loan"],
                "health": ["fit one", "gym"],
                "house expenses": ["wohnung", "miete", "landeshochschulkasse"],
            }

            matched_category = None
            for category, keywords in keyword_map.items():
                if any(k in desc for k in keywords):
                    matched_category = category.title()
                    break

            # Step 2: Fallback to LLM if needed
            if not matched_category:
                print(f"\n🤖 LLM guessing for: {tx['description']} | {tx['amount']}")
                try:
                    prompt = f"""You are a financial assistant.
Classify this transaction into a category like Groceries, Commute, Subscriptions, Debt, Health, Clothing, Entertainment, or House Expenses.

Transaction: '{tx['description']}' | Amount: {tx['amount']} | Date: {tx['date']}

Respond ONLY with the best-fit category name."""
                    response = llm_client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=10
                    )
                    matched_category = response.choices[0].message.content.strip().title()
                except Exception as e:
                    print("⚠️ LLM error:", str(e))
                    matched_category = "Others"

            matched_type = category_map.get(matched_category, "uncategorized")

            # Confirm with user
            print(f"\n🔍 Transaction: {tx['description']} | {tx['amount']} on {tx['date']}")
            print(f"💡 Suggest → Category: {matched_category}, Type: {matched_type}")
            choice = input("✅ Accept this update? [yes/no/skip]: ").strip().lower()

            if choice == "yes":
                tx["category"] = matched_category
                tx["type"] = matched_type
                updated.append(tx)
            elif choice == "no":
                custom_cat = input("📝 Enter custom category: ").strip().title()
                custom_type = category_map.get(custom_cat, input(f"⚙️ No type mapping found. Enter type (Needs/Wants/Savings): ").strip().title())
                tx["category"] = custom_cat
                tx["type"] = custom_type
                updated.append(tx)
            else:
                skipped.append(tx)

    # Save updated list
    with open(db_path, "w") as f:
        json.dump(transactions, f, indent=2)

    return {
        "message": f"Categorized {len(updated)} transactions. Skipped {len(skipped)}.",
        "updated_count": len(updated),
        "skipped_count": len(skipped)
    }

# -----------------------------------------
# 📊 Tool: Summarize Category Spending
# -----------------------------------------
@register_tool(tags=["budgeting"])
def summarize_category_spending(category: str, month: Optional[str] = None) -> Dict:
    """
    Tool Name: summarize_category_spending

    Description:
        - Calculates the total amount spent in a specific category or budgeting type (e.g., 'Groceries' or 'Needs')
          from the persistent transaction database. Supports optional month filtering.

    Arguments:
        category (str): Can be a fine-grained category (e.g., 'Groceries', 'Clothing') 
                        or a high-level type (e.g., 'Needs', 'Wants', 'Savings')
        month (Optional[str]): Natural language month filter like 'March', 'March 2025'.
                               If omitted, shows all-time data.

    Returns:
        {
            "category": <str>,
            "month": <YYYY-MM or 'all'>,
            "total_spent": <float>,
            "transactions": <List[Dict]>,
            "message": <summary string>
        }
    """
    import os
    import json
    import re

    # Normalize and parse month to YYYY-MM
    month = month.strip() if month else None
    if month:
        month = month.lower()
        year = datetime.now().year
        match = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)", month, re.IGNORECASE)
        month_names = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }
        if match:
            m = match.group(1).lower()
            if re.search(r"\d{4}", month):
                year = re.search(r"\d{4}", month).group()
            month = f"{year}-{month_names[m]}"
        else:
            month = None

    # Normalize label
    label = category.strip().title()
    is_type = label in {"Needs", "Wants", "Savings"}
    is_all = label == "All"

    try:
        with open("data/transactions.json", "r") as f:
            transactions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"message": "No transactions found."}

    # Filter by month + category/type
    matched = []
    for tx in transactions:
        if month and tx.get("date", "")[:7] != month:
            continue
        if is_all:
            matched.append(tx)
        elif is_type:
            if tx.get("type", "").title() != label:
                matched.append(tx)
        else:
            if tx.get("category", "").title() != label:
                matched.append(tx)

    total = sum(abs(tx.get("amount", 0)) for tx in matched)
    return {
        "category": label,
        "month": month or "all",
        "total_spent": round(total, 2),
        "transactions": matched,
        "message": f"You spent €{round(total, 2)} on {label} in {month or 'all time'}."
    }

# -----------------------------------------
# 📊 Tool: Query Category Spending
# -----------------------------------------

@register_tool(tags=["budgeting", "query", "spending", "category"])
def query_category_spending(category: str) -> dict:
    """
    Tool Name: query_category_spending
    Description:
        Routes natural-language category queries like "groceries in March" or "expenses last month"
        to the appropriate budget summarization logic.

    Args:
        category (str): Natural phrase from user, e.g., "groceries in March"

    Returns:
        Dictionary with total spending, matched transactions, and summary message.
    """
    import re
    from datetime import datetime
    from tools.budgeting_tools import summarize_category_spending

    category_lower = category.strip().lower()
    month_match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)",
        category_lower,
        re.IGNORECASE,
    )

    # Step 1: Extract Month in YYYY-MM format if possible
    if month_match:
        month_name = month_match.group(0).title()
        month_number = datetime.strptime(month_name, "%B").month
        year_match = re.search(r"\b(20\d{2})\b", category_lower)
        year = int(year_match.group(0)) if year_match else datetime.now().year
        month_str = f"{year}-{month_number:02d}"
        cleaned_category = (
            category_lower.replace(f"in {month_name.lower()}", "")
            .replace(month_name.lower(), "")
            .strip()
        )
    elif "last month" in category_lower:
        today = datetime.today()
        month = today.month - 1 or 12
        year = today.year if today.month > 1 else today.year - 1
        month_str = f"{year}-{month:02d}"
        cleaned_category = category_lower.replace("last month", "").strip()
    elif "this month" in category_lower:
        month_str = datetime.now().strftime("%Y-%m")
        cleaned_category = category_lower.replace("this month", "").strip()
    else:
        month_str = datetime.now().strftime("%Y-%m")
        cleaned_category = category_lower

    # Step 2: Check for general "spending" or "expenses" phrasing
    general_terms = {"expenses", "spending", "total", "total spending"}
    if any(term in cleaned_category for term in general_terms):
        return summarize_category_spending("All", month_str)

    # Step 3: Normalize category to title case
    cleaned_category = (
        cleaned_category.replace("in", "").replace("on", "").strip().title()
    )

    return summarize_category_spending(cleaned_category, month_str)

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