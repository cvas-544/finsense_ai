"""
Script Name: date_helpers.py
Author: Vasu Chukka
Created: 2025-04-21
Last Modified: 2025-04-21
Description: Utility functions for extracting date or month references from natural language
             inputs such as "this month", "last month", or "in March".
"""

import re
from typing import Tuple
from datetime import datetime, timedelta
import calendar

def extract_month_from_phrase(text: str) -> Tuple[str, str]:
    """
    Extracts the target month (YYYY-MM) from natural language phrases.
    
    Examples:
        "clothing in March"        → ("Clothing", "2025-03")
        "subscriptions last month" → ("Subscriptions", "2025-03")
        "groceries this month"     → ("Groceries", "2025-04")
        "eating out in 2023-12"    → ("Eating Out", "2023-12")

    Args:
        text (str): Natural language query or category phrase.

    Returns:
        (category: str, month: str): Normalized category name and resolved month string in YYYY-MM format.
    """
    now = datetime.now()
    lowered = text.lower()

    # 1. Handle relative month terms
    if "last month" in lowered:
        month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        category = lowered.replace("last month", "").strip()
    elif "this month" in lowered:
        month = now.strftime("%Y-%m")
        category = lowered.replace("this month", "").strip()
    else:
        # 2. Absolute month names (e.g., "in March")
        months = list(calendar.month_name)
        for i, name in enumerate(months):
            if name and name.lower() in lowered:
                month = f"{now.year}-{i:02d}"
                category = lowered.replace(name.lower(), "").replace("in", "").strip()
                break
        else:
            # 3. ISO style format like "in 2023-12"
            iso_match = re.search(r"(\d{4})[-/](\d{2})", lowered)
            if iso_match:
                year, month_part = iso_match.groups()
                month = f"{year}-{month_part}"
                category = re.sub(r"in \d{4}[-/]\d{2}", "", lowered).strip()
            else:
                # 4. Fallback to current month
                month = now.strftime("%Y-%m")
                category = text.strip()

    return category.title(), month
