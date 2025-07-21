import json
import os
from datetime import datetime

# Add imports for database access
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from utils.db_connection import get_db_connection

load_dotenv()

def get_all_transactions(user_id: str):
    """
    Loads all transactions for a specific user from the RDS PostgreSQL database.

    Args:
        user_id (str): UUID of the user whose transactions to fetch.

    Returns:
        List[Dict]: Parsed transactions or empty list on error.
    """
    try:
        connection = psycopg2.connect(
            host=os.getenv("PG_HOST"),
            database=os.getenv("PG_DATABASE"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            port=os.getenv("PG_PORT"),
        )
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC",
            (user_id,)
        )
        transactions = cursor.fetchall()
        print(f"📊 {len(transactions)} transactions loaded for user {user_id} from RDS.")
        cursor.close()
        connection.close()
        return transactions
    except Exception as e:
        print(f"❌ Failed to load transactions from RDS for user {user_id}: {e}")
        return []

def derive_month_from_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m")
    except Exception:
        return None

def get_transactions_by_month(user_id: str, month: str):
    """
    Retrieves transactions for a specific user and month directly from the database.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM transactions
            WHERE user_id = %s AND month = %s
            ORDER BY date DESC
        """, (user_id, month))
        results = cur.fetchall()
        cur.close()
        conn.close()
        print(f"📊 {len(results)} transactions for user {user_id} in {month}")
        return results
    except Exception as e:
        print(f"❌ Failed to fetch monthly transactions from RDS: {e}")
        return []