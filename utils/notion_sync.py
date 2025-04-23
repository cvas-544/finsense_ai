"""
File: notion_sync.py
Author: Vasu Chukka
Created: 2025-04-22
Description:
    Secure and robust Notion integration module for syncing PDFs and transactions.
    - Loads token from environment variables
    - Handles API errors and missing fields gracefully
    - Provides functions for fetching and later pushing data
"""

import os
from typing import List, Dict, Optional
from notion_client import Client
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# ----------------------------------------
# 🔐 Secure Token Loading
# ----------------------------------------

NOTION_TOKEN = os.getenv("NOTION_API_KEY")
if not NOTION_TOKEN:
    raise EnvironmentError("❌ NOTION_TOKEN not found. Please set it in your environment or .env file.")

notion = Client(auth=NOTION_TOKEN)

# ----------------------------------------
# 🗂️ Your Notion Database IDs (Update these)
# ----------------------------------------

PDF_UPLOADS_DB_ID = "1dd8efee976f80e3b9f9f1703e5ba8ca"
TRANSACTIONS_DB_ID = "1dd8efee976f808eb9d2d0221f599ff0"
AGENT_SUGGESTIONS_DB_ID = "1dd8efee976f80df8d55d586c0c2dbb3"
BUDGET_SUMMARY_DB_ID = "1dd8efee976f8051bdbbf62cca2c5215"
SYNC_LOGS_DB_ID = "1dd8efee976f809ab1fbe1bfaf5877c8"

# ----------------------------------------
# 📥 Fetch Transactions from Notion
# ----------------------------------------

def fetch_transactions_from_notion() -> List[Dict]:
    print("🔄 Fetching transactions from Notion...")
    try:
        results = notion.databases.query(database_id=TRANSACTIONS_DB_ID)["results"]
    except Exception as e:
        print(f"❌ Error syncing transactions: {e}")
        return []

    transactions = []
    for row in results:
        try:
            props = row["properties"]
            transactions.append({
                "date": props["Date"]["date"]["start"],
                "amount": float(props["Amount"]["number"]),
                "description": props["Description"]["title"][0]["plain_text"],
                "category": props["Category"]["select"]["name"] if props["Category"]["select"] else "uncategorized",
            })
        except Exception as e:
            print(f"⚠️ Skipped malformed transaction row: {e}")
    return transactions

# ----------------------------------------
# 📥 Fetch PDF Uploads
# ----------------------------------------

def fetch_pdf_uploads_from_notion() -> List[Dict]:
    """
    Fetches uploaded PDF metadata from the Notion database.
    Each entry includes ID, title, status, and file download URL.
    """
    try:
        results = notion.databases.query(database_id=PDF_UPLOADS_DB_ID)["results"]
    except Exception:
        return []

    uploads = []
    for row in results:
        try:
            props = row["properties"]
            files = props.get("File", {}).get("files", [])

            file_url = None
            if files:
                first_file = files[0]
                if "file" in first_file:
                    file_url = first_file["file"].get("url")

            uploads.append({
                "id": row["id"],
                "title": props["Name"]["title"][0]["plain_text"],
                "status": props["Status"]["select"]["name"] if props["Status"]["select"] else "unknown",
                "file": file_url,
            })
        except Exception:
            continue  # Skip malformed rows silently

    return uploads

# ----------------------------------------
# ✅ Future Push Helpers
# ----------------------------------------

def push_suggestion_to_notion(suggestion: Dict) -> bool:
    # Placeholder for later step
    pass

def push_summary_to_notion(summary: Dict) -> bool:
    # Placeholder for later step
    pass

# ----------------------------------------
# 🧪 Manual Test
# ----------------------------------------

if __name__ == "__main__":
    txs = fetch_transactions_from_notion()
    print(f"✅ Pulled {len(txs)} transactions")

    pdfs = fetch_pdf_uploads_from_notion()
    print(f"✅ Pulled {len(pdfs)} PDF uploads")
