"""
File: notion_sync_runner.py
Author: Vasu Chukka
Created: 2025-04-22
Last Modified: 2025-05-01
Description:
    Full Notion sync runner for FinSense Agent.
    - Downloads PDFs from Notion and parses them
    - Updates Notion PDF Status (Parsed/Error)
    - Merges transactions into local store
    - Handles deduplication, auto-categorization, and logging
    - Normalizes amounts and handles uncategorized transactions with LLM support
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
    PDF_UPLOADS_DB_ID,
)
from utils.constants import TRANSACTIONS_PATH, NOTION_PDF_DIR
from utils.query_parser import llm_client
from tools.budgeting_tools import auto_categorize_transactions, import_pdf_transactions

def sync_from_notion():
    # 1. 🔄 Fetch new PDFs from Notion
    pdfs = fetch_pdf_uploads_from_notion()
    for pdf in pdfs:
        url = pdf["file"]
        name = pdf["title"].replace(" ", "_") + ".pdf"
        path = os.path.join(NOTION_PDF_DIR, name)
        notion_page_id = pdf["id"]

        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(path, "wb") as f:
                    f.write(response.content)
                print(f"✅ Downloaded {name}")
            else:
                print(f"⚠️ Failed to download {name} (status {response.status_code})")
                continue
        except Exception as e:
            print(f"❌ Error downloading {name}: {str(e)}")
            continue

        try:
            parsed_result = import_pdf_transactions(file_path=path)
            print(f"✅ Imported {parsed_result['stored']} transactions from {name}")
            notion.pages.update(page_id=notion_page_id, properties={"Status": {"select": {"name": "Parsed"}}})
        except Exception as e:
            print(f"❌ Failed to import {name}: {e}")
            notion.pages.update(page_id=notion_page_id, properties={"Status": {"select": {"name": "Error"}}})

    # 2. 💾 Merge Notion transactions
    try:
        with open(TRANSACTIONS_PATH, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    seen_keys = {f"{tx['date']}|{tx['amount']}|{tx['description']}" for tx in existing}
    new_transactions = fetch_transactions_from_notion()

    clean_transactions = []
    pending_categorization = []
    inserted = 0

    for tx in new_transactions:
        key = f"{tx['date']}|{tx['amount']}|{tx['description']}"
        if key not in seen_keys:
            tx = normalize_notion_transaction(tx)
            if tx.get("type") in ["Needs", "Wants", "Savings"]:
                if tx["type"] in ["Needs", "Wants"]:
                    tx["amount"] = -abs(tx["amount"])
                elif tx["type"] == "Savings":
                    tx["amount"] = abs(tx["amount"])
                clean_transactions.append(tx)
                inserted += 1
            else:
                pending_categorization.append(tx)

    existing.extend(clean_transactions)
    with open(TRANSACTIONS_PATH, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"📥 Merged {inserted} new transactions from Notion")

    if pending_categorization:
        ask_and_categorize_uncategorized(pending_categorization)

    # 3. 🧠 Auto Categorize after merge
    auto_categorize_transactions()

    # 4. 🪵 Log to Sync Logs database
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"Synced {inserted} transactions and {len(pdfs)} PDFs at {timestamp}"

    payload = {
        "parent": {"database_id": SYNC_LOGS_DB_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": f"Sync on {timestamp}"}}]},
            "Details": {"rich_text": [{"text": {"content": message}}]},
        }
    }

    try:
        notion.pages.create(**payload)
        print(f"📝 Sync log written to Notion: {message}")
    except Exception as e:
        print(f"⚠️ Notion sync failed: {e}")

def normalize_notion_transaction(tx: dict) -> dict:
    tx.setdefault("type", "uncategorized")
    tx["amount"] = float(tx.get("amount", 0))
    return tx

def ask_and_categorize_uncategorized(transactions: list):
    print(f"\n⚡ {len(transactions)} uncategorized transactions found.")
    choice = input("🤖 Would you like me to auto-categorize them using AI? [yes/no]: ").strip().lower()
    if choice != "yes":
        print("❌ Skipping auto-categorization.")
        return

    categorized = []
    for tx in transactions:
        print(f"\n🔍 Transaction: {tx.get('description')} | Amount: {tx.get('amount')}")

        prompt = f"""Classify the following transaction into Needs, Wants, or Savings only:
                     Description: {tx.get('description')}
                     Amount: {tx.get('amount')}
                     Date: {tx.get('date')}
                     Respond ONLY with Needs, Wants, or Savings."""

        response = llm_client.chat.completions.create(
            model="gpt-4-0613",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5
        )

        guess = response.choices[0].message.content.strip().title()
        print(f"💡 LLM Suggests: {guess}")

        confirm = input(f"✅ Accept this categorization? [yes/no/custom]: ").strip().lower()

        if confirm == "yes":
            tx["type"] = guess
        elif confirm == "custom":
            custom_type = input("📝 Enter custom type (Needs/Wants/Savings): ").strip().title()
            tx["type"] = custom_type
        else:
            tx["type"] = "uncategorized"

        if tx["type"] in ["Needs", "Wants"]:
            tx["amount"] = -abs(tx["amount"])
        elif tx["type"] == "Savings":
            tx["amount"] = abs(tx["amount"])

        categorized.append(tx)

    if categorized:
        with open(TRANSACTIONS_PATH, "r") as f:
            existing = json.load(f)
        existing.extend(categorized)
        with open(TRANSACTIONS_PATH, "w") as f:
            json.dump(existing, f, indent=2)
        print("✅ Completed auto-categorization and saved to database.")