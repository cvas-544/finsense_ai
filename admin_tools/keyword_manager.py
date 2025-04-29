"""
File: admin_tools/keyword_manager.py
Author: Vasu Chukka
Created: 2025-05-01
Description:
    Admin tool to manually add expense or income keywords
    into the keyword mapping JSON database.
"""

import json
import os

KEYWORDS_PATH = "data/expense_income_keywords.json"

def add_keyword_admin(keyword_type: str, word: str):
    """
    Admin-only function to add a new keyword.

    Args:
        keyword_type: 'expense' or 'income'
        word: Merchant name or keyword string
    """
    if not os.path.exists(KEYWORDS_PATH):
        keywords = {"expense_keywords": [], "income_keywords": []}
    else:
        with open(KEYWORDS_PATH, "r") as f:
            keywords = json.load(f)

    if keyword_type not in ["expense", "income"]:
        raise ValueError("Type must be 'expense' or 'income'.")

    key = f"{keyword_type}_keywords"
    if word.lower() not in (w.lower() for w in keywords[key]):
        keywords[key].append(word.strip())
        with open(KEYWORDS_PATH, "w") as f:
            json.dump(keywords, f, indent=2)
        print(f"✅ Admin: Added '{word}' to '{keyword_type}' keywords.")
    else:
        print(f"⚠️ Admin: '{word}' already exists in '{keyword_type}' keywords.")