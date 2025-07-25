"""
Script Name: budgeting_tools.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-20
Description: Cleaned and enhanced version of budgeting tools module.
"""

import re
import os
import uuid
import json, calendar
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict, Union, Optional
from tools.shared_registry import register_tool
from memory.memory_store import Memory


from utils.date_helpers import extract_month_from_phrase
from utils.db_connection import get_db_connection
from utils.transactions_store import get_all_transactions  # replaces extract_transactions_from_db - Make sure this exists
from utils.category_groups import load_merged_category_groups     # Or wherever you load category mappings
from utils.transactions_store import get_transactions_by_month
from utils.expense_income_keywords import load_expense_income_keywords

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
def _load_profile() -> Dict:
    return {}  # Deprecated: Previously used local JSON

def _save_profile(profile: Dict):
    pass  # Deprecated: Previously used local JSON

    
# ----------------------------
# Tool: 🗂️ Add User Category Keyword
# ----------------------------

@register_tool(tags=["categorization", "user_keywords"])
def add_user_category_keyword(user_id: str, group_name: str, keyword: str) -> str:
    """
    Adds a new keyword to a user's category group.

    Args:
        user_id: UUID of the user
        group_name: Category group (e.g. 'food', 'health')
        keyword: New keyword to associate

    Returns:
        Confirmation message
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_category_keywords (user_id, group_name, keyword)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, keyword) DO NOTHING
        """, (user_id, group_name.lower(), keyword.lower()))
        conn.commit()
        cur.close()
        conn.close()
        return f"✅ Added keyword '{keyword}' to group '{group_name}' for user {user_id}."
    except Exception as e:
        return f"❌ Failed to add keyword: {e}"


# ----------------------------
# Tool: 🧠 Fuzzy Match Helper
# ----------------------------

def fuzzy_match_transaction_rds(user_id: str, match_str: str) -> Optional[Dict]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT transaction_id, description, amount, date, category, type
            FROM transactions
            WHERE user_id = %s AND description ILIKE %s
            ORDER BY date DESC
            LIMIT 1
        """, (user_id, f"%{match_str}%"))

        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return {
                "transaction_id": row[0],
                "description": row[1],
                "amount": row[2],
                "date": row[3],
                "category": row[4],
                "type": row[5]
            }
        return None
    except Exception as e:
        print(f"❌ Error matching transaction: {e}")
        return None # Deprecated: Previously matched against local JSON

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
    return []  # Deprecated: Previously extracted from local JSON

# ----------------------------
# 📄 Tool: Parse Bank PDF
# ----------------------------

@register_tool(tags=["budgeting"])
def parse_bank_pdf(user_id: str, file_path: str) -> Dict:
    """
    Parses a PDF bank statement and inserts parsed transactions into the RDS database.

    Args:
        user_id (str): UUID of the user who owns the transactions.
        file_path (str): Path to the PDF bank statement file.

    Returns:
        Dict: Summary of imported transactions.
    """
    import json
    import os
    import re
    import uuid
    import pdfplumber
    from datetime import datetime
    from utils.db_connection import get_db_connection
    from tools.budgeting_tools import load_merged_category_groups

    transactions = []
    merged_keywords = load_merged_category_groups(user_id)

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().splitlines()
            for line in lines:
                match = re.match(r"^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+(-?\d+,\d{2})\s?€?$", line)
                if not match:
                    continue

                date_str, desc, amount_str = match.groups()
                try:
                    date = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                    amount = float(amount_str.replace(".", "").replace(",", "."))
                    desc_lower = desc.lower()

                    # Step 1: Match group
                    matched_group = None
                    for group, keywords in merged_keywords.items():
                        if any(k.lower() in desc_lower for k in keywords):
                            matched_group = group
                            break
                    category = matched_group if matched_group else "Uncategorized"

                    # Step 2: Get type from RDS category_type_mapping or fallback
                    conn = get_db_connection()
                    cur = conn.cursor()

                    cur.execute("SELECT budget_type FROM category_type_mapping WHERE category = %s", (category,))
                    row = cur.fetchone()
                    type_ = row[0] if row else "Uncategorized"

                    # Step 3: Fallback to expense/income keyword table if still Uncategorized
                    if type_ == "Uncategorized":
                        cur.execute("""
                            SELECT category FROM expense_income_keywords
                            WHERE LOWER(%s) LIKE '%%' || LOWER(keyword) || '%%'
                            LIMIT 1
                        """, (desc_lower,))
                        row = cur.fetchone()
                        if row:
                            fallback_category = row[0]
                            if fallback_category == "expense":
                                type_ = "Needs"
                                amount = -abs(amount)
                            elif fallback_category == "income":
                                type_ = "Savings"
                                amount = abs(amount)
                        else:
                            amount = -abs(amount)  # default to expense sign

                    else:
                        # Sign normalization based on resolved type
                        if type_ in ["Needs", "Wants"]:
                            amount = -abs(amount)
                        elif type_ == "Savings":
                            amount = abs(amount)

                    cur.close()
                    conn.close()

                    transactions.append({
                        "transaction_id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "date": date,
                        "amount": amount,
                        "description": desc.strip(),
                        "category": category,
                        "type": type_,
                        "month": date[:7]
                    })

                except Exception as e:
                    print(f"⚠️ Parsing error on line: '{line}' → {e}")

    # Insert into RDS
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        inserted = 0
        for tx in transactions:
            try:
                cur.execute("""
                    INSERT INTO transactions (
                        transaction_id, user_id, date, amount, description, category, type, month
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    tx["transaction_id"], tx["user_id"], tx["date"], tx["amount"],
                    tx["description"], tx["category"], tx["type"], tx["month"]
                ))
                inserted += 1
            except Exception as e:
                print(f"⚠️ Failed to insert transaction: {e}")

        conn.commit()
        cur.close()
        conn.close()

        return {
            "message": f"✅ Imported {inserted} transactions from {os.path.basename(file_path)}.",
            "inserted": inserted,
            "failed": len(transactions) - inserted
        }

    except Exception as e:
        return {"message": f"❌ Database error: {e}"}

# -----------------------------------------
# 🧾 Tool: Record a New Income Source
# -----------------------------------------

@register_tool(tags=["budgeting"])
def record_income_source(user_id: str, source_name: str, amount: float) -> str:
    """
    Adds a new income source to the RDS `other_income_sources` table.

    Args:
        user_id: UUID of the user.
        source_name: Name of the income source (e.g., 'freelance', 'rental')
        amount: Amount received from this source

    Returns:
        Confirmation message
    """
    from utils.db_connection import get_db_connection

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO other_income_sources (user_id, source_name, amount)
            VALUES (%s, %s, %s)
        """, (user_id, source_name.strip().title(), round(amount, 2)))

        conn.commit()
        cur.close()
        conn.close()

        return f"✅ Income source '{source_name.strip().title()}' of €{amount:.2f} recorded successfully for user {user_id}."

    except Exception as e:
        return f"❌ Error recording income source: {e}"

# ----------------------------
# 💳 Tool: Record Transaction
# ----------------------------

@register_tool(tags=["budgeting"])
def record_transaction(date: str, amount: float, description: str, category: str = "Uncategorized") -> Dict:
    """
    Records a new transaction with correct sign normalization.
    Infers type based on either keyword match or category_type_mapping table.
    Inserts transaction into RDS.
    """
    from utils.db_connection import get_db_connection

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

    description_clean = description.strip()
    desc_lower = description_clean.lower()
    category_normalized = category.strip().title()
    type_ = "Uncategorized"
    user_id = "00000000-0000-0000-0000-000000000000"  # Fallback user

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Step 1: Check if description matches any known expense/income keyword
        cur.execute("SELECT category FROM expense_income_keywords")
        keywords = [row[0].lower() for row in cur.fetchall()]
        if any(k in desc_lower for k in keywords):
            if any(k in desc_lower for k in keywords if k in ["salary", "refund", "deposit", "income", "reimbursement", "cashback"]):
                type_ = "Savings"
                category_normalized = "Income"
            else:
                type_ = "Needs"
                category_normalized = "General Expense"

        # Step 2: Try lookup from category_type_mapping table
        cur.execute("SELECT budget_type FROM category_type_mapping WHERE category = %s", (category_normalized,))
        row = cur.fetchone()
        if row:
            type_ = row[0]
        else:
            print(f"⚠️ Category '{category_normalized}' not found in category_type_mapping.")
            decision = input("🛠️ Would you like to define this category now? [yes/no]: ").strip().lower()
            if decision == "yes":
                type_input = input("🔵 Enter type for this category (Needs/Wants/Savings): ").strip().title()
                if type_input in ["Needs", "Wants", "Savings"]:
                    type_ = type_input
                    cur.execute("INSERT INTO category_type_mapping (category, budget_type) VALUES (%s, %s)", (category_normalized, type_))
                    print(f"✅ Saved mapping: {category_normalized} → {type_}")
                else:
                    print("❌ Invalid input. Defaulting to 'Uncategorized'.")
            else:
                print("⚠️ Proceeding as 'Uncategorized'.")

        # Step 3: Normalize amount sign
        if type_ in ["Needs", "Wants"]:
            amount = -abs(amount)
        elif type_ == "Savings":
            amount = abs(amount)
        else:
            amount = -abs(amount)

        # Step 4: Insert into DB
        cur.execute("""
            INSERT INTO transactions (
                transaction_id, user_id, date, amount, description, category, type, month
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()), user_id, date, amount, description_clean,
            category_normalized, type_, date[:7]
        ))

        conn.commit()
        cur.close()
        conn.close()

        return {
            "message": f"✅ Transaction recorded under {category_normalized} ({type_}).",
            "transaction": {
                "date": date,
                "amount": amount,
                "description": description_clean,
                "category": category_normalized,
                "type": type_,
                "month": date[:7]
            }
        }

    except Exception as e:
        return {
            "message": "❌ Error recording transaction.",
            "error": str(e)
        }

# ----------------------------
# 🧾 Tool: Categorize Transactions
# ----------------------------

@register_tool(tags=["budgeting", "manual_categorization", "label_transaction"])
def categorize_transactions(user_id: str, transactions: Union[str, List[Dict]]) -> List[Dict]:
    """
    Categorizes a specific transaction or list of transactions into budgeting types (Needs/Wants/Savings)
    based on keyword rules from merged category groups (global + user-specific) and category_type_mapping in RDS.

    Args:
        user_id (str): UUID of the user
        transactions (Union[str, List[Dict]]): A fuzzy search string or list of transaction dicts

    Returns:
        List[Dict]: Categorized transactions with 'category' and 'type'
    """
    from utils.category_groups import load_merged_category_groups
    from utils.db_connection import get_db_connection

    # Fuzzy match if input is a string
    if isinstance(transactions, str):
        match = fuzzy_match_transaction_rds(transactions)
        if match:
            transactions = [match]
        else:
            raise ValueError("No matching transaction found in database.")

    group_map = load_merged_category_groups(user_id)

    # Preload type mapping from DB
    type_lookup = {}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT category, budget_type FROM category_type_mapping")
        rows = cur.fetchall()
        for cat, typ in rows:
            type_lookup[cat.lower()] = typ
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Failed to load type mapping: {e}")

    categorized = []
    for tx in transactions:
        desc = tx.get("description", "").lower()
        matched_group = None

        for group_name, keywords in group_map.items():
            if any(k.lower() in desc for k in keywords):
                matched_group = group_name.title()
                break

        category = matched_group if matched_group else "Uncategorized"
        budget_type = type_lookup.get(category.lower(), "Uncategorized")

        tx["category"] = category
        tx["type"] = budget_type
        categorized.append(tx)

    return categorized

# ----------------------------
# 📊 Tool: Summarize Budget
# ----------------------------
@register_tool(tags=["budgeting", "summarize"])
def summarize_budget(user_id: str, month: str) -> str:
    """
    Summarizes the user's spending against the 50/30/20 budget rule for a given month.

    Automatically runs auto-categorization for any uncategorized transactions.

    Args:
        user_id (str): UUID of the user.
        month (str): Target month in YYYY-MM format.

    Returns:
        str: Budget summary text.
    """
    from utils.db_connection import get_db_connection
    from tools.budgeting_tools import auto_categorize_transactions

    try:
        # 🔁 Categorize any uncategorized transactions before summarizing
        print("🔁 Running auto-categorization before budget summary...")
        auto_categorize_transactions(user_id)

        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Fetch user monthly income and budget preference
        cur.execute("""
            SELECT monthly_income, budget_ratio_choice
            FROM user_profile
            WHERE user_id = %s
        """, (user_id,))
        result = cur.fetchone()
        if not result:
            return f"❌ User profile not found for user_id {user_id}."

        monthly_income, ratio = float(result[0]), result[1]
        if not monthly_income or monthly_income <= 0:
            return f"❌ Monthly income is not set for this user."

        # 2. Parse budget ratios
        ratio_parts = [float(r) for r in ratio.split("/")]
        if len(ratio_parts) != 3 or sum(ratio_parts) != 100:
            return f"❌ Invalid budget ratio format: {ratio}"

        budget = {
            "Needs": monthly_income * ratio_parts[0] / 100,
            "Wants": monthly_income * ratio_parts[1] / 100,
            "Savings": monthly_income * ratio_parts[2] / 100
        }

        # 3. Sum spending by type from transactions table
        cur.execute("""
            SELECT type, SUM(amount)
            FROM transactions
            WHERE user_id = %s AND month = %s AND amount < 0
            GROUP BY type
        """, (user_id, month))
        rows = cur.fetchall()

        actual = {"Needs": 0, "Wants": 0, "Savings": 0}
        for t_type, amt in rows:
            t_type = t_type.title()
            if t_type in actual:
                actual[t_type] += abs(amt)

        cur.close()
        conn.close()

        # 4. Compose summary
        lines = [f"📊 Budget summary for {month}:"]
        for t in ["Needs", "Wants", "Savings"]:
            a = actual.get(t, 0)
            b = budget.get(t, 0)
            status = "✅ under" if a <= b else "⚠️ over"
            lines.append(f"- {t}: spent €{a:.2f} of €{b:.2f} ({status})")
        return "\n".join(lines)

    except Exception as e:
        return f"❌ Failed to summarize budget: {e}"

# -------------------------------
# 📊 Tool: Summarize Incomes
# -------------------------------

@register_tool(tags=["budgeting"])
def summarize_income(user_id: str) -> Dict:
    """
    Summarizes the total income for a user by combining:
    - Monthly base salary from user_profile
    - Additional income sources from other_income table

    Args:
        user_id (str): UUID of the user

    Returns:
        Dict: Summary with total income and income sources
    """
    from utils.db_connection import get_db_connection

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Base salary
        cur.execute("SELECT monthly_income FROM user_profile WHERE user_id = %s", (user_id,))
        base_result = cur.fetchone()
        base_income = base_result[0] if base_result else 0.0
        sources = []
        if base_income > 0:
            sources.append({"source": "Salary", "amount": float(base_income)})

        # Other income sources
        cur.execute("""
            SELECT source, amount FROM other_income_sources
            WHERE user_id = %s
        """, (user_id,))
        rows = cur.fetchall()
        for source_name, amount in rows:
            sources.append({"source": source_name, "amount": float(amount)})

        cur.close()
        conn.close()

        total = sum(s["amount"] for s in sources)
        return {
            "total_income": round(total, 2),
            "sources": sources,
            "message": f"Total income: €{round(total, 2)}"
        }

    except Exception as e:
        return {
            "message": "❌ Failed to summarize income.",
            "error": str(e),
            "total_income": 0.0,
            "sources": []
        }

# ----------------------------
# 📊 Tool: Update transactions
# ----------------------------

@register_tool(tags=["budgeting"])
def update_transaction(
    user_id: str,
    transaction_match: str,
    new_description: Optional[str] = None,
    new_amount: Optional[Union[float, str]] = None,
    new_date: Optional[str] = None,
    new_category: Optional[str] = None,
    new_type: Optional[str] = None
) -> str:
    """
    Updates details of an existing transaction already stored in the RDS database.

    This tool is intended for user-initiated edits to transaction fields like amount, description, category, or date.

    ⚠️ Do NOT use this tool for initial classification or fuzzy guessing.
    For categorization purposes, use `categorize_transactions()` or `auto_categorize_transactions()` instead.

    Args:
        user_id (str): ID of the user.
        transaction_match (str): Partial string to match the transaction's description.
        new_description (Optional[str]): Updated description.
        new_amount (Optional[Union[float, str]]): Updated amount.
        new_date (Optional[str]): Updated date.
        new_category (Optional[str]): Updated category.
        new_type (Optional[str]): Explicit type (Needs/Wants/Savings).

    Returns:
        str: Update status.
    """
    from utils.db_connection import get_db_connection

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Step 1: Find matching transaction
        cur.execute("""
            SELECT transaction_id, description, amount, date, category, type
            FROM transactions
            WHERE user_id = %s AND description ILIKE %s
            ORDER BY date DESC
            LIMIT 1
        """, (user_id, f"%{transaction_match}%"))
        row = cur.fetchone()

        if not row:
            return f"No matching transaction found for '{transaction_match}'."

        transaction_id, description, amount, date, category, type_ = row

        # Step 2: Apply updates
        if new_description:
            description = new_description
        if new_amount:
            try:
                amount = float(new_amount)
            except ValueError:
                return "Invalid amount format."
        if new_date:
            if new_date == "today":
                date = datetime.now().strftime("%Y-%m-%d")
            elif new_date == "yesterday":
                date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                date = new_date
        if new_category:
            category = new_category.title()

        if new_type:
            type_ = new_type.title()

        # Reload type mapping from RDS if category changed
        if new_category:
            cur.execute("SELECT budget_type FROM category_type_mapping WHERE category = %s", (category,))
            result = cur.fetchone()
            if result:
                type_ = result[0]
            else:
                type_ = type_ or "Uncategorized"

        month = date.strftime("%Y-%m") if isinstance(date, datetime) else str(date)[:7]

        # Step 3: Update the transaction
        cur.execute("""
            UPDATE transactions
            SET description = %s,
                amount = %s,
                date = %s,
                category = %s,
                type = %s,
                month = %s
            WHERE transaction_id = %s
        """, (description, amount, date, category, type_, month, transaction_id))

        conn.commit()
        cur.close()
        conn.close()

        return f"✅ Transaction updated: {description} on {date} for {amount:.2f} ({category}, {type_})."

    except Exception as e:
        return f"❌ Failed to update transaction: {e}"

# -----------------------------------------
# 📥 Tool: Import and Store PDF Transactions
# -----------------------------------------

@register_tool(tags=["budgeting"])
def import_pdf_transactions(file_path: str) -> Dict:
    """
    Parses a PDF bank statement and stores categorized transactions in the RDS database.
    Also saves raw dump locally for audit/debugging.
    Skips duplicates based on (date, amount, description).
    """
    import os
    import re
    import json
    import uuid
    from datetime import datetime
    import pdfplumber
    from utils.db_connection import get_db_connection
    from tools.budgeting_tools import load_merged_category_groups

    user_id = "00000000-0000-0000-0000-000000000000"  # Default/fallback user

    # Load dynamic keyword → category groups from RDS
    category_groups = load_merged_category_groups(user_id)

    # Load category → type map from RDS
    category_type_map = {}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT category, budget_type FROM category_type_mapping")
        category_type_map = {cat: t for cat, t in cur.fetchall()}
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Failed to load category-type mapping from RDS: {e}")

    transactions = []
    raw_transactions = []

    # 1. Parse PDF
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().splitlines()
            for line in lines:
                match = re.match(r"^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+(-?\d+,\d{2})\s?\u20ac?$", line)
                if match:
                    date_str, desc, amount_str = match.groups()
                    try:
                        date = datetime.strptime(date_str, "%d.%m.%Y")
                        iso_date = date.strftime("%Y-%m-%d")
                        month_tag = date.strftime("%Y-%m")
                        amount = float(amount_str.replace(".", "").replace(",", "."))
                        desc_lower = desc.strip().lower()

                        # Match category based on description
                        matched_category = "Other"
                        for group, keywords in category_groups.items():
                            if any(k.lower() in desc_lower for k in keywords):
                                matched_category = group.title()
                                break

                        # Match type from RDS category_type_mapping
                        type_ = category_type_map.get(matched_category, "Uncategorized")

                        # Sign normalization
                        if type_ == "Needs" or type_ == "Wants":
                            amount = -abs(amount)
                        elif type_ == "Savings":
                            amount = abs(amount)
                        else:
                            type_ = "Uncategorized" # Default to negative unless explicitly Savings
                            amount = -abs(amount)

                        raw_transactions.append({
                            "date": iso_date,
                            "amount": amount,
                            "description": desc.strip()
                        })

                        transactions.append({
                            "transaction_id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "date": iso_date,
                            "month": month_tag,
                            "amount": amount,
                            "description": desc.strip(),
                            "category": matched_category,
                            "type": type_,
                            "source": os.path.basename(file_path)
                        })
                    except Exception as e:
                        print(f"⚠️ Failed to parse line: {line} ({e})")

    if not transactions:
        print("⚠️ No transactions found in the PDF.")
        return {
            "message": "No valid transactions found in the uploaded PDF. Please make sure it's a supported bank statement.",
            "stored": 0,
            "raw_dump": None,
            "transactions": []
        }

    # 2. Save raw dump
    raw_dir = "data/parsed_pdfs/raw"
    os.makedirs(raw_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    base_name = os.path.basename(file_path).replace(".pdf", "").replace(" ", "_")
    raw_path = os.path.join(raw_dir, f"{base_name}_{ts}.json")
    with open(raw_path, "w") as f:
        json.dump(raw_transactions, f, indent=2)

    # 3. Insert into RDS with deduplication
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        inserted = 0
        for tx in transactions:
            cur.execute("""
                SELECT COUNT(*) FROM transactions
                WHERE user_id = %s AND date = %s AND amount = %s AND description = %s
            """, (tx["user_id"], tx["date"], tx["amount"], tx["description"]))
            exists = cur.fetchone()[0] > 0
            if exists:
                continue

            cur.execute("""
                INSERT INTO transactions (
                    transaction_id, user_id, date, month, amount, description, category, type, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                tx["transaction_id"], tx["user_id"], tx["date"], tx["month"], tx["amount"],
                tx["description"], tx["category"], tx["type"], tx["source"]
            ))
            inserted += 1

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Failed to insert into RDS: {e}")
        return {"message": "Database insert failed.", "error": str(e)}

    return {
        "message": f"Imported {inserted} new transactions from PDF and inserted into RDS.",
        "stored": inserted,
        "raw_dump": raw_path,
        "transactions": transactions
    }

# -----------------------------------------
# 🧾 Tool: Auto Categorize the transactions
# -----------------------------------------

@register_tool(tags=["budgeting", "autocategorize", "auto", "clean_uncategorized", "smart_categorization"])
def auto_categorize_transactions(user_id: str) -> Dict:
    """
    Auto-categorizes uncategorized transactions for a given user using merged keyword rules, LLM fallback,
    and dynamic category updates. All updates are stored in RDS.
    """
    from tools.budgeting_tools import llm_client
    from utils.db_connection import get_db_connection
    from utils.category_groups import load_merged_category_groups

    keyword_map = load_merged_category_groups(user_id)
    updated = []
    skipped = []

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Load uncategorized transactions
        cur.execute("""
            SELECT transaction_id, date, amount, description
            FROM transactions
            WHERE user_id = %s AND type = 'Uncategorized'
            ORDER BY date DESC
        """, (user_id,))
        transactions = cur.fetchall()

        # Load category → type mapping
        cur.execute("SELECT category, budget_type FROM category_type_mapping")
        category_type_map = {cat: typ for cat, typ in cur.fetchall()}

        for tx_id, date, amount, desc in transactions:
            desc_lower = desc.lower()
            matched_category = None

            # 1. Try keyword match
            for group, keywords in keyword_map.items():
                if any(k.lower() in desc_lower for k in keywords):
                    matched_category = group.title()
                    break

            # 2. Fallback to LLM if no match
            if not matched_category:
                prompt = f"""You are a financial assistant helping to categorize bank transactions.
                Your task:
                - Classify the following transaction into exactly ONE category like Groceries, Commute, Subscriptions, 
                  Debt, Health, Clothing, Entertainment, House Expenses, or Savings.
                - Respond ONLY with the category name.
                - No explanation. No sentences. Only the category word.

                Transaction details:
                - Description: {desc}
                - Amount: {amount}
                - Date: {date}

                Answer with ONLY the category word."""
                try:
                    response = llm_client.chat.completions.create(
                        model="gpt-4-0613",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=10
                    )
                    matched_raw = response.choices[0].message.content.strip()
                    matched_category = matched_raw.title() if len(matched_raw.split()) == 1 else "Others"
                except Exception:
                    matched_category = "Others"

            print(f"\n🔍 Transaction: {desc} | {amount} on {date}")
            print(f"💡 Suggest → Category: {matched_category}")
            while True:
                choice = input("✅ Accept this update? [yes/no/skip]: ").strip().lower()
                if choice in ["yes", "no", "skip"]:
                    break
                else:
                    print("⚠️ Please enter only 'yes', 'no', or 'skip'.")

            if choice == "yes":
                category = matched_category
                if category not in category_type_map:
                    category_type = input(f"⚙️ Enter type for {category} (Needs/Wants/Savings): ").strip().title()
                    if category_type in ["Needs", "Wants", "Savings"]:
                        category_type_map[category] = category_type
                        cur.execute("""
                            INSERT INTO category_type_mapping (category, budget_type)
                            VALUES (%s, %s)
                            ON CONFLICT (category) DO NOTHING
                        """, (category, category_type))
                    else:
                        category_type = "Uncategorized"
                else:
                    category_type = category_type_map[category]

            elif choice == "no":
                category = input("📝 Enter custom category: ").strip().title()
                if category not in category_type_map:
                    category_type = input(f"⚙️ Enter type for {category} (Needs/Wants/Savings): ").strip().title()
                    if category_type in ["Needs", "Wants", "Savings"]:
                        category_type_map[category] = category_type
                        cur.execute("""
                            INSERT INTO category_type_mapping (category, budget_type)
                            VALUES (%s, %s)
                            ON CONFLICT (category) DO NOTHING
                        """, (category, category_type))
                    else:
                        category_type = "Uncategorized"
                else:
                    category_type = category_type_map[category]
            else:
                skipped.append({
                    "transaction_id": tx_id,
                    "description": desc,
                    "amount": amount,
                    "date": date
                })
                continue

            # 3. Update DB
            try:
                cur.execute("""
                    UPDATE transactions
                    SET category = %s, type = %s
                    WHERE transaction_id = %s
                """, (category, category_type, tx_id))
                updated.append({
                    "transaction_id": tx_id,
                    "description": desc,
                    "amount": amount,
                    "date": date
                })
            except Exception as e:
                print(f"❌ Failed to update transaction {tx_id}: {e}")

        conn.commit()
        cur.close()
        conn.close()

        return {
            "message": f"✅ Categorized {len(updated)} transactions. Skipped {len(skipped)}.",
            "updated_count": len(updated),
            "skipped_count": len(skipped)
        }

    except Exception as e:
        return {"message": f"❌ Error during auto-categorization: {e}"}

# -----------------------------------------
# 📊 Tool: Summarize Category Spending
# -----------------------------------------
# File: tools/budgeting_tools.py

@register_tool(tags=["budgeting", "summarize"])
def summarize_category_spending(user_id: str, month: str, category: str) -> str:
    """
    Summarizes total spending for a given category and month using the latest transaction data.

    This tool:
    - Auto-categorizes uncategorized transactions first
    - Fetches transactions from RDS using the user_id
    - Expands the user-requested category using merged category group mappings
    - Filters only negative (expense) transactions
    - Supports the 'All' category for total spending
    - Returns a human-readable summary
    """

    # 🧠 Step 0: Auto-categorize uncategorized entries
    print(f"🔁 Running auto-categorization for user {user_id} before category summary...")
    auto_categorize_transactions(user_id)

    print(f"🔍 Filtering for month = {month}, category = {category.lower()} for user {user_id}")
    transactions = get_transactions_by_month(user_id, month)
    print(f"📂 Retrieved {len(transactions)} transactions from RDS for user {user_id}")

    category_groups = load_merged_category_groups(user_id)
    category_input = category.strip().lower()
    expanded_categories = category_groups.get(category_input, [category_input])
    expanded_categories = [c.lower() for c in expanded_categories]

    matched = []
    for tx in transactions:
        if not isinstance(tx.get("amount"), (int, float)) or tx["amount"] >= 0:
            continue  # Skip income
        tx_category = tx.get("category", "").strip().lower()
        if category_input == "all" or tx_category in expanded_categories:
            matched.append(tx)

    total_spent = sum(abs(tx["amount"]) for tx in matched)
    pretty_category = "all categories" if category_input == "all" else category_input.title()
    print(f"✅ Matched {len(matched)} transactions totaling €{total_spent:.2f}")

    return f"You spent €{total_spent:.2f} on {pretty_category} in {month}."


# -----------------------------------------
# 📊 Tool: Query Category Spending (Natural Language)
# -----------------------------------------

@register_tool(tags=["budgeting", "query", "spending", "category"])
def query_category_spending(user_id: str, query: str) -> Dict:
    """
    Tool Name: query_category_spending

    Description:
        Parses a natural-language query like "groceries in March 2025"
        and routes it to the summarizer.

    Args:
        user_id (str): UUID of the user.
        query (str): Natural-language phrase, e.g., "groceries in March"

    Returns:
        Dict: Spending summary details.
    """
    label, month_str = extract_month_from_phrase(query)

    # Default to 'All' if generic words are used
    if any(tok in label.lower() for tok in ("expense", "spending", "total")):
        label = "All"

    summary_text = summarize_category_spending(user_id=user_id, month=month_str, category=label)
    return {
        "query": query,
        "month": month_str,
        "category": label,
        "summary": summary_text
    }

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