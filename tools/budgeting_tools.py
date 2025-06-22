"""
Script Name: budgeting_tools.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-20
Description: Cleaned and enhanced version of budgeting tools module.
"""

import re
import os
import json, calendar
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict, Union, Optional
from tools.shared_registry import register_tool
from memory.memory_store import Memory
from utils.date_helpers import extract_month_from_phrase
from utils.transactions_store import get_all_transactions  # replaces extract_transactions_from_db

# Initializes the OpenAI client using the API key from environment variables.
load_dotenv()
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------------------
# File: tools/budgeting_tools.py
# -----------------------------------------
TRANSACTIONS_PATH = "data/transactions.json"

# ----------------------------
# Tool: 🧠 Profile loader
# ----------------------------
PROFILE_PATH = "data/default_profile.json"

def _load_profile() -> Dict:
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    try:
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_profile(profile: Dict):
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)

# ------------------------------
# Tool: 🗂️ Load Category Groups
# ------------------------------
def load_category_groups() -> Dict[str, List[str]]:
    path = "data/category_groups.json"
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    else:
        return {}

# ----------------------------
# Tool: 🗓️ Parse Month
# ----------------------------
def _parse_month(month_str: str) -> str:
    m = re.search(
        r"(january|february|march|april|may|june|july|"
        r"august|september|october|november|december)"
        r"(?:\s+(\d{4}))?",
        month_str.strip(),
        re.IGNORECASE
    )
    if not m:
        return None
    month_name = m.group(1).lower()
    year = m.group(2) or str(datetime.now().year)
    month_map = {name: f"{idx:02d}" for idx, name in enumerate(calendar.month_name) if idx}
    return f"{year}-{month_map[month_name]}"

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

# def extract_transactions_from_db() -> List[Dict]:
#     """
#     Loads all categorized transactions from the persistent JSON database.

#     Returns:
#         A list of transactions with both 'category' and 'type' fields.
#     """
#     try:
#         with open("data/transactions.json", "r") as f:
#             transactions = json.load(f)
#     except (FileNotFoundError, json.JSONDecodeError):
#         return []

#     return [
#         tx for tx in transactions
#         if isinstance(tx, dict) and "category" in tx and "type" in tx
#     ]

def extract_transactions_from_db():
    import os
    path = "data/transactions.json"
    print(f"📂 Reading transactions from: {os.path.abspath(path)}")
    with open(path, "r") as f:
        transactions = json.load(f)
    print(f"📊 {len(transactions)} transactions loaded.")
    return transactions

# ----------------------------
# 📄 Tool: Parse Bank PDF
# ----------------------------

@register_tool(tags=["budgeting"])
def parse_bank_pdf(file_path: str) -> List[Dict]:
    import pdfplumber
    import re
    from datetime import datetime
    import json
    import os

    # Load dynamic keyword list
    keywords_path = "data/expense_income_keywords.json"
    if os.path.exists(keywords_path):
        with open(keywords_path, "r") as f:
            keywords = json.load(f)
        expense_keywords = [word.lower() for word in keywords.get("expense_keywords", [])]
        income_keywords = [word.lower() for word in keywords.get("income_keywords", [])]
    else:
        expense_keywords = []
        income_keywords = []

    transactions = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().splitlines()
            for line in lines:
                match = re.match(r"^(\d{2}\.\d{2}\.\d{4}) (.+?) (-?\d+,\d{2}) €?$", line)
                if match:
                    date_str, desc, amount_str = match.groups()
                    try:
                        date = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                        amount = float(amount_str.replace(".", "").replace(",", "."))
                        desc_lower = desc.lower()

                        # Normalize amount sign
                        if amount > 0:
                            if any(word in desc_lower for word in expense_keywords):
                                amount = -abs(amount)
                            elif any(word in desc_lower for word in income_keywords):
                                amount = abs(amount)
                            else:
                                amount = -abs(amount)

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
    Adds a new income source to default_profile.json under 'income_sources'.
    Stores all sources in a JSON file.

    Args:
        source_name: Name of the income source (e.g., 'freelance', 'rental')
        amount: Amount received from this source

    Returns:
        Confirmation message
    """
    try:
        profile = _load_profile()
        sources = profile.get("income_sources", [])
        sources.append({"source": source_name, "amount": round(amount, 2)})
        profile["income_sources"] = sources
        _save_profile(profile)
        return f"Income source '{source_name}' of €{amount:.2f} recorded successfully."
    except Exception as e:
        return f"Error recording income source: {e}"
    
# -----------------------------------------
# 💼 Tool: Record Base Salary
# -----------------------------------------

@register_tool(tags=["budgeting"])
def record_income(amount: float) -> str:
    """
    Records the user's monthly income into default_profile.json under 'income'.
    
    Args:
        amount: Monthly income in euros or rupees
    
    Returns:
        Confirmation message
    """
    try:
        profile = _load_profile()
        profile["income"] = round(amount, 2)
        _save_profile(profile)
        return f"Income of €{amount:.2f} recorded successfully."
    except Exception as e:
        return f"Failed to record income: {e}"

# ----------------------------
# 💳 Tool: Record Transaction
# ----------------------------

@register_tool(tags=["budgeting"])
def record_transaction(date: str, amount: float, description: str, category: str = "uncategorized") -> Dict:
    """
    Records a new transaction with correct sign normalization based on category type.
    Handles dynamic addition of new categories if missing.
    """

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
    mapping_path = "data/category_type_mapping.json"
    try:
        with open(mapping_path, "r") as f:
            mapping = json.load(f)
    except FileNotFoundError:
        mapping = {}

    category_normalized = category.strip().title()
    type_ = mapping.get(category_normalized)

    if not type_:
        print(f"⚠️ Warning: Category '{category_normalized}' not found in mapping.")
        decision = input("🛠️ Would you like to define this category now? [yes/no]: ").strip().lower()
        if decision == "yes":
            type_ = input("🔵 Enter type for this category (Needs/Wants/Savings): ").strip().title()
            if type_ not in ["Needs", "Wants", "Savings"]:
                print("❌ Invalid type entered. Defaulting category to 'uncategorized'.")
                type_ = "uncategorized"
            else:
                # Save the new category mapping
                mapping[category_normalized] = type_
                with open(mapping_path, "w") as f:
                    json.dump(mapping, f, indent=2)
                print(f"✅ Added '{category_normalized}' as {type_}.")
        else:
            type_ = "uncategorized"
            print(f"⚠️ Proceeding with type 'uncategorized'.")

    # Normalize amount based on type
    if type_ in ["Needs", "Wants"]:
        amount = -abs(amount)
    elif type_ == "Savings":
        amount = abs(amount)
    else:
        amount = -abs(amount)

    # Create transaction object
    transaction = {
    "id": f"txn_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "date": date,
    "month": date[:7], 
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
def summarize_budget(transactions: List[Dict], budgets: Dict[str, Dict[str, float]], month: str) -> str:
    """
    Summarizes the user's spending against the 50/30/20 budget rule.
    Loads transactions and income from default_profile.json.
    """
    if month not in budgets:
        return f"No budgets for {month}."
    budget_for_month = budgets[month]
    spent = {}
    # sum spend per category
    for tx in transactions:
        date = tx.get("date","")
        if not date.startswith(month):
            continue
        cat = tx.get("category","Unknown").strip().title()
        amt = tx.get("amount", 0)
        if isinstance(amt,(int,float)):
            spent[cat] = spent.get(cat, 0.0) + amt
    # union of categories
    all_cats = set(budget_for_month.keys()) | set(spent.keys())
    lines = []
    for cat in sorted(all_cats):
        s = spent.get(cat, 0.0)
        b = budget_for_month.get(cat, 0.0)
        status = "under" if s <= b else "over"
        lines.append(f"{cat}: spent {s:.1f} of {b:.1f}, {status} budget.")
    return "\n".join(lines)

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

    # 1. Load base salary from default_profile.json
    profile = _load_profile()
    sources = []
    if profile.get("income",0) > 0:
        sources.append({"source":"salary","amount":profile["income"]})
    sources.extend(profile.get("income_sources",[]))

    total = sum(src.get("amount",0) for src in sources)
    return {
        "total_income": round(total,2),
        "sources": sources,
        "message": f"Total income: €{round(total,2)}"
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
    raw_dir = "data/parsed_pdfs/raw"
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
    meta_path = "data/parsed_pdfs/metadata.json"
    os.makedirs("data/parsed_pdfs", exist_ok=True)
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
    "raw_dump": raw_path,
    "transactions": new_txs  # ← Add this line!
    }

# -----------------------------------------
# 🧾 Tool: Auto Categorize the transactions
# -----------------------------------------

@register_tool(tags=["budgeting", "autocategorize", "auto", "clean_uncategorized", "smart_categorization"])
def auto_categorize_transactions(transactions: Optional[List[Dict]] = None) -> Dict:
    """
    Auto-categorizes transactions using keyword rules, LLM fallback, and dynamic category updates.

    - Processes all transactions with type 'uncategorized'.
    - First attempts keyword-based matching using known merchant keywords.
    - If keyword matching fails, falls back to LLM suggestion for category guessing.
    - Prompts the user for confirmation or manual correction before updating each transaction.
    - Dynamically saves new category-to-type mappings into category_type_mapping.json if the user defines them.
    - Enforces correct amount signs based on assigned transaction type:
        • Needs/Wants → Negative amounts
        • Savings → Positive amounts
    - Saves updated transactions and updated category mappings automatically.

    This tool can be run:
    - Before budget summarization (to ensure clean categorized data)
    - Directly by user request to clean up uncategorized entries

    Args:
        transactions (Optional[List[Dict]]): 
            List of transactions to process. 
            If None, loads transactions from the local database (transactions.json).

    Returns:
        Dict: Summary containing update counts and status message.
    """
    import os
    import json
    from tools.budgeting_tools import llm_client

    db_path = "data/transactions.json"
    mapping_path = "data/category_type_mapping.json"

    try:
        with open(db_path, "r") as f:
            transactions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"message": "No transaction database found."}

    try:
        with open(mapping_path, "r") as f:
            category_map = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        category_map = {}

    keyword_map = {
        "groceries": ["rewe", "edeka", "aldi", "dm", "apotheke", "drillisch"],
        "subscriptions": ["netflix", "spotify", "vodafone", "pyur"],
        "commute": ["db vertrieb", "flixbus", "bahn"],
        "debt": ["klarna", "advanzia", "loan"],
        "health": ["fit one", "gym"],
        "house expenses": ["wohnung", "miete", "landeshochschulkasse"]
    }

    updated = []
    skipped = []

    for tx in transactions:
        if tx.get("type", "").lower() == "uncategorized":
            desc = tx.get("description", "").lower()
            matched_category = None

            # Step 1: Keyword Rule Matching
            for category, keywords in keyword_map.items():
                if any(k in desc for k in keywords):
                    matched_category = category.title()
                    break

            # Step 2: Fallback to LLM if needed
            if not matched_category:
                prompt = f"""You are a financial assistant helping to categorize bank transactions.
                                Your task:
                                - Classify the following transaction into exactly ONE category like Groceries, Commute, Subscriptions, 
                                  Debt, Health, Clothing, Entertainment, House Expenses, or Savings.
                                - Respond ONLY with the category name.
                                - No explanation. No sentences. Only the category word.

                                Transaction details:
                                - Description: {tx.get('description')}
                                - Amount: {tx.get('amount')}
                                - Date: {tx.get('date')}

                                Answer with ONLY the category word.
                         """
                try:
                    response = llm_client.chat.completions.create(
                        model="gpt-4-0613",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=10
                    )
                    matched_raw = response.choices[0].message.content.strip()
                    if len(matched_raw.split()) == 1:
                        matched_category = matched_raw.title()
                    else:
                        print(f"⚠️ LLM returned invalid category '{matched_raw}'. Defaulting to 'Others'.")
                        matched_category = "Others"
                except Exception as e:
                    matched_category = "Others"

            print(f"\n🔍 Transaction: {tx.get('description')} | {tx.get('amount')} on {tx.get('date')}")
            print(f"💡 Suggest → Category: {matched_category}")
            while True:
                choice = input("✅ Accept this update? [yes/no/skip]: ").strip().lower()
                if choice in ["yes", "no", "skip"]:
                    break
                else:
                    print("⚠️ Please enter only 'yes', 'no', or 'skip'.")

            if choice == "yes":
                tx["category"] = matched_category
                tx["type"] = category_map.get(matched_category, input(f"⚙️ No type mapping found. Enter type (Needs/Wants/Savings): ").strip().title())

                # Enforce correct amount sign
                if tx["type"] in ["Needs", "Wants"]:
                    tx["amount"] = -abs(tx["amount"])
                elif tx["type"] == "Savings":
                    tx["amount"] = abs(tx["amount"])

                # Save new category mapping dynamically if needed
                if matched_category not in category_map:
                    category_map[matched_category] = tx["type"]

                updated.append(tx)

            elif choice == "no":
                custom_cat = input("📝 Enter custom category: ").strip().title()
                custom_type = category_map.get(custom_cat, input(f"⚙️ No type mapping found. Enter type (Needs/Wants/Savings): ").strip().title())
                tx["category"] = custom_cat
                tx["type"] = custom_type

                if custom_type in ["Needs", "Wants"]:
                    tx["amount"] = -abs(tx["amount"])
                elif custom_type == "Savings":
                    tx["amount"] = abs(tx["amount"])

                # Save new mapping
                if custom_cat not in category_map:
                    category_map[custom_cat] = custom_type

                updated.append(tx)

            else:
                skipped.append(tx)

    # Save updated transactions
    with open(db_path, "w") as f:
        json.dump(transactions, f, indent=2)

    # Save updated category map
    with open(mapping_path, "w") as f:
        json.dump(category_map, f, indent=2)

    return {
        "message": f"Categorized {len(updated)} transactions. Skipped {len(skipped)}.",
        "updated_count": len(updated),
        "skipped_count": len(skipped)
    }

# -----------------------------------------
# 📊 Tool: Summarize Category Spending
# -----------------------------------------
# File: tools/budgeting_tools.py

# @register_tool(tags=["budgeting", "summarize"])
# def summarize_category_spending(transactions: List[Dict], month: str, category: str) -> str:
#     """
#     Summarizes total spending for a given category and month from the transaction database.

#     - Expands user-requested categories into related sub-categories using category_groups.json.
#     - Filters transactions by matching the provided month against either transaction date or month field.
#     - Only negative (expense) transactions are counted toward spending totals.
#     - Ignores income (positive) transactions.
#     - Supports summarizing across all categories if the requested category is "All".
#     - Formats the output cleanly for user display.

#     Args:
#         transactions (List[Dict]): 
#             List of all available transactions from the database.
#         month (str): 
#             Target month in YYYY-MM format (e.g., '2025-03').
#         category (str): 
#             User-requested category to summarize (e.g., 'Food', 'Entertainment', 'All').

#     Returns:
#         str: 
#             A summary sentence stating the total amount spent for the requested category and month.
#     """

#     category_groups = load_category_groups()
#     category_input = category.strip().lower()

#     # Expand the category into list of possible matching categories
#     expanded_categories = category_groups.get(category_input, [category_input])
#     expanded_categories = [c.lower() for c in expanded_categories]

#     total_spent = 0.0
#     for tx in transactions:
#         tx_date = tx.get("date", "")
#         tx_month = tx.get("month", "")

#         # Filter by month
#         if not (tx_date.startswith(month) or tx_month == month):
#             continue

#         tx_category = tx.get("category", "").strip().lower()
#         amt = tx.get("amount", 0)

#         if not isinstance(amt, (int, float)) or amt >= 0:
#             continue  # Only expenses (negative amounts)

#         # Match category
#         if category_input == "all" or tx_category in expanded_categories:
#             total_spent += amt

#     total_spent_display = abs(total_spent)
#     pretty_category = "all categories" if category_input == "all" else category_input.title()

#     return f"You spent €{total_spent_display:.2f} on {pretty_category} in {month}."

from utils.transactions_store import get_all_transactions  # Make sure this exists
from utils.category_groups import load_category_groups     # Or wherever you load category mappings

@register_tool(tags=["budgeting", "summarize"])
def summarize_category_spending(month: str, category: str) -> str:
    """
    Summarizes total spending for a given category and month using the latest transaction data.

    This tool:
    - Loads transactions from disk at runtime (not from agent memory)
    - Expands the user-requested category using category_groups.json
    - Filters only negative (expense) transactions
    - Supports the 'All' category for total spending
    - Returns a human-readable summary

    Args:
        month (str): Target month in YYYY-MM format (e.g., '2025-03')
        category (str): User-requested category to summarize (e.g., 'Groceries', 'All')

    Returns:
        str: Spending summary
    """

    print(f"🔍 Filtering for month = {month}, category = {category.lower()}")

    transactions = get_all_transactions()
    print(f"📂 Reading transactions from memory... {len(transactions)} total records")

    category_groups = load_category_groups()
    category_input = category.strip().lower()
    expanded_categories = category_groups.get(category_input, [category_input])
    expanded_categories = [c.lower() for c in expanded_categories]

    matched = []
    for tx in transactions:
        if not isinstance(tx.get("amount"), (int, float)) or tx["amount"] >= 0:
            continue  # Skip income
        tx_month = tx.get("month", "") or tx.get("date", "")[:7]
        tx_category = tx.get("category", "").strip().lower()
        if tx_month != month:
            continue
        if category_input == "all" or tx_category in expanded_categories:
            matched.append(tx)

    total_spent = sum(abs(tx["amount"]) for tx in matched)
    pretty_category = "all categories" if category_input == "all" else category_input.title()
    print(f"✅ Matched {len(matched)} transactions totaling €{total_spent:.2f}")
    
    print(f"🔍 Filtering for month = {month}, category = {category.lower()}")
    print(f"📂 Reading transactions... {len(transactions)} total records")

    return f"You spent €{total_spent:.2f} on {pretty_category} in {month}."


# -----------------------------------------
# 📊 Tool: Query Category Spending
# -----------------------------------------

# @register_tool(tags=["budgeting", "query", "spending", "category"])
# def query_category_spending(nl_query: str) -> Dict:
#     """
#     Tool Name: query_category_spending

#     Description:
#         Routes a natural-language query like "groceries in March 2025"
#         to the summarizer.

#     Args:
#         category (str): Natural phrase from user, e.g., "groceries in March"

#     Returns:
#         Dictionary with total spending, matched transactions, and summary message.
#     """
#     # 1) Parse category + month
#     label, month_str = extract_month_from_phrase(nl_query)

#     # 2) Detect generic spending queries
#     if any(tok in label.lower() for tok in ("expense", "spending", "total")):
#         label = "All"

#     # 3) Delegate
#     return summarize_category_spending(label, month_str)


# def query_category_spending(category: str, month: str = None) -> dict:
#     """
#     Tool Name: query_category_spending
#     Description:
#         Routes natural-language category queries like "groceries in March"
#         or "expenses last month" to the appropriate summarizer.

#     Args:
#         nl (str): Natural-language query, e.g. "eating out in March 2025"

#     Returns:
#         Dict with total spending, matched transactions, and summary message.
#     """
#     nl = category.strip().lower()

#     # 1) Extract month name + optional year
#     month_regex = re.compile(
#         r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b", 
#         re.IGNORECASE
#     )
#     m = month_regex.search(nl)
#     if m:
#         month_name = m.group(1).title()
#         month_num = datetime.strptime(month_name, "%B").month
#         year_match = re.search(r"\b(20\d{2})\b", nl)
#         year = int(year_match.group(1)) if year_match else datetime.now().year
#         month_str = f"{year}-{month_num:02d}"
#         # Remove the “in March” (or just “March”) from the phrase:
#         nl_cleaned = re.sub(rf"\b(in\s+)?{month_name.lower()}\b", "", nl).strip()
#     elif "last month" in nl:
#         today = datetime.today()
#         prev_month = today.month - 1 or 12
#         prev_year = today.year if today.month > 1 else today.year - 1
#         month_str = f"{prev_year}-{prev_month:02d}"
#         nl_cleaned = nl.replace("last month", "").strip()
#     else:
#         # default to this month
#         month_str = datetime.now().strftime("%Y-%m")
#         nl_cleaned = nl

#     # 2) If they asked “expenses” in general, use “All”
#     if any(tok in nl_cleaned for tok in ("expense", "spending", "total")):
#         cat = "All"
#     else:
#         # Title-case the remainder to match your categories
#         cat = nl_cleaned.title()

#     # 3) Finally call your summarizer
#     return summarize_category_spending(cat, month_str)

# @register_tool(tags=["budgeting", "query", "spending", "category"])
# def query_category_spending(category: str) -> dict:
#     """
#     Tool Name: query_category_spending
#     Description:
#         Routes natural-language category queries like "groceries in March" or "expenses last month"
#         to the appropriate budget summarization logic.

#     Args:
#         category (str): Natural phrase from user, e.g., "groceries in March"

#     Returns:
#         Dictionary with total spending, matched transactions, and summary message.
#     """
#     import re
#     from datetime import datetime
#     from tools.budgeting_tools import summarize_category_spending

#     category_lower = category.strip().lower()
#     month_match = re.search(
#         r"(january|february|march|april|may|june|july|august|september|october|november|december)",
#         category_lower,
#         re.IGNORECASE,
#     )

#     # Step 1: Extract Month in YYYY-MM format if possible
#     if month_match:
#         month_name = month_match.group(0).title()
#         month_number = datetime.strptime(month_name, "%B").month
#         year_match = re.search(r"\b(20\d{2})\b", category_lower)
#         year = int(year_match.group(0)) if year_match else datetime.now().year
#         month_str = f"{year}-{month_number:02d}"
#         cleaned_category = (
#             category_lower.replace(f"in {month_name.lower()}", "")
#             .replace(month_name.lower(), "")
#             .strip()
#         )
#     elif "last month" in category_lower:
#         today = datetime.today()
#         month = today.month - 1 or 12
#         year = today.year if today.month > 1 else today.year - 1
#         month_str = f"{year}-{month:02d}"
#         cleaned_category = category_lower.replace("last month", "").strip()
#     elif "this month" in category_lower:
#         month_str = datetime.now().strftime("%Y-%m")
#         cleaned_category = category_lower.replace("this month", "").strip()
#     else:
#         month_str = datetime.now().strftime("%Y-%m")
#         cleaned_category = category_lower

#     # Step 2: Check for general "spending" or "expenses" phrasing
#     general_terms = {"expenses", "spending", "total", "total spending"}
#     if any(term in cleaned_category for term in general_terms):
#         return summarize_category_spending("All", month_str)

#     # Step 3: Normalize category to title case
#     cleaned_category = (
#         cleaned_category.replace("in", "").replace("on", "").strip().title()
#     )

#     return summarize_category_spending(cleaned_category, month_str)

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