"""
File: notion_sync_runner.py
Author: Vasu Chukka
Created: 2025-04-22
Last Modified: 2025-04-23
Description:
    Full Notion sync runner for FinSense Agent.
    - Downloads PDFs from Notion and parses them
    - Merges transactions into local store
    - Handles deduplication and logging
"""

from datetime import datetime
import os
import json
import requests
from utils.notion_sync import (
    notion,
    fetch_pdf_uploads_from_notion,
    fetch_transactions_from_notion,
    SYNC_LOGS_DB_ID,
)
from utils.constants import TRANSACTIONS_PATH, NOTION_PDF_DIR
from tools.budgeting_tools import auto_categorize_transactions, import_pdf_transactions

def sync_from_notion():
    # -------------------------------
    # 1. 🔄 Fetch new PDFs from Notion
    # -------------------------------
    pdfs = fetch_pdf_uploads_from_notion()
    for pdf in pdfs:
        url = pdf["file"]
        name = pdf["title"].replace(" ", "_") + ".pdf"
        path = os.path.join(NOTION_PDF_DIR, name)
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(path, "wb") as f:
                    f.write(response.content)
                print(f"✅ Downloaded {name}")
            else:
                print(f"⚠️ Failed to download {name} (status {response.status_code})")
        except Exception as e:
            print(f"❌ Error downloading {name}: {str(e)}")
        
        # ✅ Now parse and merge into transaction DB
        try:
            parsed_result = import_pdf_transactions(file_path=path)
            print(f"✅ Imported {len(parsed_result['transactions'])} transactions from {name}")
        except Exception as e:
            print(f"❌ Failed to import {name}: {e}")

    # -------------------------------
    # 2. 💾 Merge Notion transactions
    # -------------------------------
    try:
        with open(TRANSACTIONS_PATH, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    seen_keys = {f"{tx['date']}|{tx['amount']}|{tx['description']}" for tx in existing}
    new_transactions = fetch_transactions_from_notion()

    inserted = 0
    for tx in new_transactions:
        key = f"{tx['date']}|{tx['amount']}|{tx['description']}"
        if key not in seen_keys:
            existing.append(tx)
            inserted += 1

    with open(TRANSACTIONS_PATH, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"📥 Merged {inserted} new transactions from Notion")

    # -------------------------------
    # 3. 🧠 Auto Categorize after merge
    # -------------------------------
    auto_categorize_transactions()

    # -------------------------------
    # 4. 🪵 Log to Sync Logs database
    # -------------------------------
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"Synced {inserted} transactions and {len(pdfs)} PDFs at {timestamp}"

    payload = {
        "parent": {"database_id": SYNC_LOGS_DB_ID},
        "properties": {
            "Name": {
                "title": [
                    {"text": {"content": f"Sync on {timestamp}"}}
                ]
            },
            "Details": {
                "rich_text": [
                    {"text": {"content": message}}
                ]
            }
        }
    }

    try:
        notion.pages.create(**payload)
        print(f"📝 Sync log written to Notion: {message}")
    except Exception as e:
        print(f"⚠️ Notion sync failed: {e}")
