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
from utils.transactions_store import get_all_transactions  # replaces extract_transactions_from_db
from utils.db_connection import get_db_connection
from utils.category_groups import load_merged_category_groups

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

def fuzzy_match_transaction_db(query: str) -> Optional[Dict]:
    return None  # Deprecated: Previously matched against local JSON

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
    # Load keyword list
    expense_keywords = []
    income_keywords = []
    try:
        with open("data/expense_income_keywords.json", "r") as f:
            keywords = json.load(f)
            expense_keywords = [w.lower() for w in keywords.get("expense_keywords", [])]
            income_keywords = [w.lower() for w in keywords.get("income_keywords", [])]
    except Exception as e:
        print(f"⚠️ Could not load keyword mapping: {e}")

    transactions = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().splitlines()
            for line in lines:
                match = re.match(r"^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+(-?\d+,\d{2})\s?€?$", line)
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
                            "transaction_id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "date": date,
                            "amount": amount,
                            "description": desc.strip(),
                            "category": "uncategorized",
                            "type": "uncategorized",
                            "month": date[:7]
                        })
                    except Exception as e:
                        print(f"⚠️ Parsing error on line: '{line}' → {e}")

    # Insert transactions into DB
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
    Adds a new income source to the RDS `other_income` table.

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
            INSERT INTO other_income (user_id, source_name, amount)
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
def record_transaction(date: str, amount: float, description: str, category: str = "uncategorized") -> Dict:
    """
    Records a new transaction with correct sign normalization based on category type.
    Inserts into RDS instead of local file.
    """

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

    user_id = "00000000-0000-0000-0000-000000000000"  # Temporary user_id for now

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO transactions (
                transaction_id, user_id, date, amount, description, category, type, month
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            str(uuid.uuid4()), user_id, date, amount, description,
            category_normalized, type_, date[:7]
        ))

        conn.commit()
        cur.close()
        conn.close()

        return {
            "message": f"Transaction recorded under {category_normalized} ({type_}).",
            "transaction": {
                "date": date,
                "amount": amount,
                "description": description,
                "category": category_normalized,
                "type": type_,
                "month": date[:7]
            }
        }

    except Exception as e:
        print(f"❌ Error inserting transaction into RDS: {e}")
        return {
            "message": "Error recording transaction.",
            "error": str(e)
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
@register_tool(tags=["budgeting", "summarize"])
def summarize_budget(user_id: str, month: str) -> str:
    """
    Summarizes the user's spending against the 50/30/20 budget rule for a given month.

    - Retrieves income and ratio from user_profile table
    - Sums expenses from transactions table grouped by type
    - Compares actual vs budget for Needs/Wants/Savings
    - Returns human-readable summary

    Args:
        user_id (str): UUID of the user.
        month (str): Target month in YYYY-MM format.

    Returns:
        str: Budget summary text.
    """
    from utils.db_connection import get_db_connection

    try:
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

        monthly_income, ratio = result
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
            SELECT source_name, amount FROM other_income
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

        # Reload type mapping
        try:
            with open("data/category_type_mapping.json", "r") as f:
                mapping = json.load(f)
            type_ = mapping.get(category, type_)
        except FileNotFoundError:
            type_ = type_ or "uncategorized"

        month = date[:7]

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

                        # Heuristic categorization
                        desc_lower = desc.lower()
                        if any(k in desc_lower for k in ["rewe", "edeka", "aldi", "dm", "apotheke", "rent", "drillisch"]):
                            category, type_ = "Groceries", "Needs"
                        elif any(k in desc_lower for k in ["netflix", "spotify", "starbucks", "eating", "uber"]):
                            category, type_ = "Entertainment", "Wants"
                        elif amount > 0:
                            category, type_ = "Income", "Savings"
                        else:
                            category, type_ = "Other", "uncategorized"

                        # Sign normalization
                        amount = -abs(amount) if type_ in ["Needs", "Wants"] else abs(amount)

                        raw_transactions.append({
                            "date": iso_date,
                            "amount": amount,
                            "description": desc.strip()
                        })

                        transactions.append({
                            "transaction_id": str(uuid.uuid4()),
                            "user_id": "00000000-0000-0000-0000-000000000000",
                            "date": iso_date,
                            "month": month_tag,
                            "amount": amount,
                            "description": desc.strip(),
                            "category": category,
                            "type": type_,
                            "source": os.path.basename(file_path)
                        })
                    except Exception as e:
                        print(f"\u26a0\ufe0f Failed to parse line: {line} ({e})")

    if not transactions:
        print("\u26a0\ufe0f No transactions found in the PDF.")
        return {
            "message": "No valid transactions found in the uploaded PDF. Please make sure it's a supported bank statement.",
            "stored": 0,
            "raw_dump": None,
            "transactions": []
        }

    # 2. Save raw dump for audit/debugging
    raw_dir = "data/parsed_pdfs/raw"
    os.makedirs(raw_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    base_name = os.path.basename(file_path).replace(".pdf", "").replace(" ", "_")
    raw_path = os.path.join(raw_dir, f"{base_name}_{ts}.json")
    with open(raw_path, "w") as f:
        json.dump(raw_transactions, f, indent=2)

    # 3. Store to RDS with deduplication
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
        print(f"\u274c Failed to insert into RDS: {e}")
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
    and dynamic category updates. Updates go to RDS. Category-type mapping stays in JSON.

    Args:
        user_id (str): UUID of the user whose transactions are being categorized.

    Returns:
        Dict: Summary of update and skipped counts.
    """
    import json
    from tools.budgeting_tools import llm_client
    from utils.db_connection import get_db_connection
    from utils.category_groups import load_merged_category_groups

    mapping_path = "data/category_type_mapping.json"
    try:
        with open(mapping_path, "r") as f:
            category_map = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        category_map = {}

    # ✅ Load user + global keyword mappings
    keyword_map = load_merged_category_groups(user_id)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT transaction_id, date, amount, description
            FROM transactions
            WHERE user_id = %s AND type = 'uncategorized'
            ORDER BY date DESC
        """, (user_id,))
        transactions = cur.fetchall()
    except Exception as e:
        return {"message": f"❌ Failed to load uncategorized transactions: {e}"}

    updated = []
    skipped = []

    for tx in transactions:
        desc = tx["description"].lower()
        matched_category = None

        # Step 1: Keyword Match
        for category, keywords in keyword_map.items():
            if any(k.lower() in desc for k in keywords):
                matched_category = category.title()
                break

        # Step 2: LLM Fallback
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

        print(f"\n🔍 Transaction: {tx['description']} | {tx['amount']} on {tx['date']}")
        print(f"💡 Suggest → Category: {matched_category}")
        while True:
            choice = input("✅ Accept this update? [yes/no/skip]: ").strip().lower()
            if choice in ["yes", "no", "skip"]:
                break
            else:
                print("⚠️ Please enter only 'yes', 'no', or 'skip'.")

        if choice == "yes":
            category = matched_category
            if category not in category_map:
                category_type = input(f"⚙️ Enter type for {category} (Needs/Wants/Savings): ").strip().title()
                category_map[category] = category_type
            else:
                category_type = category_map[category]

        elif choice == "no":
            category = input("📝 Enter custom category: ").strip().title()
            if category not in category_map:
                category_type = input(f"⚙️ Enter type for {category} (Needs/Wants/Savings): ").strip().title()
                category_map[category] = category_type
            else:
                category_type = category_map[category]
        else:
            skipped.append(tx)
            continue

        # Update in DB
        try:
            cur.execute("""
                UPDATE transactions
                SET category = %s, type = %s
                WHERE transaction_id = %s
            """, (category, category_type, tx["transaction_id"]))
            updated.append(tx)
        except Exception as e:
            print(f"❌ Failed to update transaction {tx['transaction_id']}: {e}")

    conn.commit()
    cur.close()
    conn.close()

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

from utils.transactions_store import get_all_transactions  # Make sure this exists
from utils.category_groups import load_category_groups     # Or wherever you load category mappings
from utils.transactions_store import get_transactions_by_month
from utils.category_groups import load_category_groups

@register_tool(tags=["budgeting", "summarize"])
def summarize_category_spending(user_id: str, month: str, category: str) -> str:
    """
    Summarizes total spending for a given category and month using the latest transaction data.

    This tool:
    - Fetches transactions from RDS using the user_id
    - Expands the user-requested category using category_groups.json
    - Filters only negative (expense) transactions
    - Supports the 'All' category for total spending
    - Returns a human-readable summary

    Args:
        user_id (str): UUID of the user.
        month (str): Target month in YYYY-MM format (e.g., '2025-03')
        category (str): User-requested category to summarize (e.g., 'Groceries', 'All')

    Returns:
        str: Spending summary
    """

    print(f"🔍 Filtering for month = {month}, category = {category.lower()} for user {user_id}")

    transactions = get_transactions_by_month(user_id, month)
    print(f"📂 Retrieved {len(transactions)} transactions from RDS for user {user_id}")

    category_groups = load_merged_category_groups()
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