"""
File: pdf_merge_from_notion.py
Author: Vasu Chukka
Created: 2025-04-23
Description:
    Parses PDFs downloaded from Notion and merges their transactions into
    the persistent database (data/transactions.json). Also saves raw parsed
    dumps for debugging or audit purposes.

    - Looks for PDFs in `data/notion_pdfs/`
    - Parses each file using `parse_bank_pdf()`
    - Saves raw dump to `data/parsed_pdfs/`
    - Adds unique transactions to `data/transactions.json`
"""

import os
import json
from datetime import datetime
from tools.budgeting_tools import parse_bank_pdf

NOTION_PDF_DIR = "data/notion_pdfs"
PARSED_PDF_DIR = "data/parsed_pdfs"
TRANSACTIONS_PATH = "data/transactions.json"


def parse_and_merge_notion_pdfs():
    os.makedirs(PARSED_PDF_DIR, exist_ok=True)

    # Load existing transactions
    try:
        with open(TRANSACTIONS_PATH, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    seen_keys = {f"{tx['date']}|{tx['amount']}|{tx['description']}" for tx in existing}
    inserted = 0

    for file in os.listdir(NOTION_PDF_DIR):
        if not file.lower().endswith(".pdf"):
            continue

        path = os.path.join(NOTION_PDF_DIR, file)
        print(f"📄 Parsing {file}...")

        try:
            transactions = parse_bank_pdf(path)
        except Exception as e:
            print(f"❌ Failed to parse {file}: {e}")
            continue

        # Save raw dump for audit/debugging
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        raw_path = os.path.join(PARSED_PDF_DIR, f"{file.replace('.pdf','')}_{timestamp}.json")
        with open(raw_path, "w") as f:
            json.dump(transactions, f, indent=2)

        for tx in transactions:
            key = f"{tx['date']}|{tx['amount']}|{tx['description']}"
            if key not in seen_keys:
                tx["source"] = file
                tx["month"] = tx["date"][:7]
                existing.append(tx)
                seen_keys.add(key)
                inserted += 1

    with open(TRANSACTIONS_PATH, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"✅ Merged {inserted} transactions from Notion PDFs.")
