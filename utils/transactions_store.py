import json
import os
from datetime import datetime

TRANSACTION_FILE = os.path.join("data", "transactions.json")

def get_all_transactions():
    """
    Loads all transactions from the main JSON database file.

    Returns:
        List[Dict]: Parsed transactions or empty list if file not found.
    """
    try:
        print(f"📂 Reading transactions from: {os.path.abspath(TRANSACTION_FILE)}")
        with open(TRANSACTION_FILE, "r") as f:
            transactions = json.load(f)
        print(f"📊 {len(transactions)} transactions loaded.")
        return transactions
    except Exception as e:
        print(f"❌ Failed to load transactions: {e}")
        return []
    
def derive_month_from_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m")
    except Exception:
        return None
    
def get_transactions_by_month(month: str):
    """
    Retrieves transactions for a specific month.
    """
    transactions = get_all_transactions()
    return [tx for tx in transactions if derive_month_from_date(tx["date"]) == month]