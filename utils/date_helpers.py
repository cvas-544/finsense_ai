"""
Script Name: date_helpers.py
Author: Vasu Chukka
Created: 2025-04-21
Last Modified: 2025-04-28
Description: Utility functions for extracting date or month references from natural language
             inputs such as "this month", "last month", or "in March", "03/2025", "2024-07", etc.
"""

import re
from typing import Tuple
from datetime import datetime, timedelta
import calendar

# def extract_month_from_phrase(text: str) -> Tuple[str, str]:
#     """
#     Extracts the target month (YYYY-MM) from natural language phrases,
#     and returns (cleaned_category, month_str).
#     Falls back to current month if no date info found.

#     Examples:
#         "clothing in March"        → ("Clothing", "2025-03")
#         "subscriptions last month" → ("Subscriptions", "2025-03")
#         "groceries this month"     → ("Groceries", "2025-04")
#         "eating out in 2023-12"    → ("Eating Out", "2023-12")
#         "expenses in Mar-2025"     → ("Expenses", "2025-03")
#         "bill for 03/2025"         → ("Bill For", "2025-03")
#         "report for 2024-07"       → ("Report For", "2024-07")
#         "target for March"         → ("Target For", "2025-03")
#     """
#     now = datetime.now()
#     lowered = text.lower()

#     # 1) Relative months
#     if "last month" in lowered:
#         month_str = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
#         cleaned = lowered.replace("last month", "")
#     elif "this month" in lowered:
#         month_str = now.strftime("%Y-%m")
#         cleaned = lowered.replace("this month", "")
#     else:
#         # 2) Month name with optional year suffix (e.g. "March", "March-2025", "Mar-2025")
#         month_names = {name.lower(): f"{i:02d}" for i, name in enumerate(calendar.month_name) if name}
#         # include 3-letter abbrevs too
#         abbrevs = {name[:3].lower(): f"{i:02d}" for i, name in enumerate(calendar.month_name) if name}
#         month_map = {**month_names, **abbrevs}

#         # regex: optional "in ", month name or abbrev, optional "-YYYY"
#         m = re.search(
#             rf"\b(?:in\s+)?(?P<mon>{'|'.join(map(re.escape, month_map))})(?:[-/](?P<yr>\d{{4}}))?\b",
#             lowered,
#             re.IGNORECASE
#         )

#         if m:
#             mon = m.group("mon").lower()
#             yr = m.group("yr") or str(now.year)
#             month_str = f"{yr}-{month_map[mon]}"
#             cleaned = re.sub(m.group(0), "", lowered, flags=re.IGNORECASE)
#         else:
#             # 3) Numeric MM/YYYY (e.g. "03/2025")
#             m2 = re.search(r"\b(?:in\s+)?(?P<m>\d{2})/(?P<y>\d{4})\b", lowered)
#             if m2:
#                 month_str = f"{m2.group('y')}-{m2.group('m')}"
#                 cleaned = re.sub(m2.group(0), "", lowered)
#             else:
#                 # 4) ISO YYYY-MM (e.g. "2024-07")
#                 m3 = re.search(r"\b(?:in\s+)?(?P<y>\d{4})-(?P<m>\d{2})\b", lowered)
#                 if m3:
#                     month_str = f"{m3.group('y')}-{m3.group('m')}"
#                     cleaned = re.sub(m3.group(0), "", lowered)
#                 else:
#                     # 5) fallback
#                     month_str = now.strftime("%Y-%m")
#                     cleaned = lowered

#     # Strip out leftover "in" if it wasn't part of month-match
#     cleaned = re.sub(r"\bin\b", "", cleaned)
#     # clean extra whitespace and punctuation
#     cleaned = cleaned.replace("-", " ").strip()
#     cleaned = re.sub(r"\s{2,}", " ", cleaned)

#     # Title-case and return
#     category = cleaned.title() if cleaned else ""
#     return category, month_str

def extract_month_from_phrase(text: str) -> Tuple[str, str]:
    """
    Extracts the target month (YYYY-MM) from natural language phrases,
    and returns (cleaned_category, month_str).
    """
    now = datetime.now()
    lowered = text.lower().strip()

    # 1) Relative phrases
    if "last month" in lowered:
        month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        category = re.sub(r"\blast month\b", "", lowered).strip()

    elif "this month" in lowered:
        month = now.strftime("%Y-%m")
        category = re.sub(r"\bthis month\b", "", lowered).strip()

    else:
        # 2) Numeric ISO or slash formats: YYYY-MM, YYYY/MM, MM-YYYY, MM/YYYY
        num_match = re.search(r"\b(\d{4}[-/]\d{2}|\d{2}[-/]\d{4})\b", lowered)
        if num_match:
            token = num_match.group(1)
            a, b = token.split(token[4] if token[4] in "-/" else token[2])
            # decide which is year vs month
            if len(a) == 4:
                year, mon = a, b
            else:
                mon, year = a, b
            month = f"{year}-{mon}"
            # strip just the numeric token (keep words like 'for')
            category = lowered.replace(token, "").strip()
            # drop any standalone 'in' or 'on'
            category = re.sub(r"\b(in|on)\b", "", category).strip()

        else:
            # 3) Full month names
            month = None
            category = lowered
            for idx, name in enumerate(calendar.month_name):
                if idx == 0: continue
                if re.search(rf"\b{name.lower()}\b", lowered):
                    month = f"{now.year}-{idx:02d}"
                    category = re.sub(rf"\b(in\s*)?{name.lower()}\b", "", lowered).strip()
                    break

            # 4) Three-letter abbreviations (Jan, Feb, Mar, …)
            if month is None:
                for idx, abbr in enumerate(calendar.month_abbr):
                    if idx == 0: continue
                    if re.search(rf"\b{abbr.lower()}\b", lowered):
                        month = f"{now.year}-{idx:02d}"
                        category = re.sub(rf"\b(in\s*)?{abbr.lower()}\b", "", lowered).strip()
                        break

            # 5) Fallback to current month if nothing matched
            if month is None:
                month = now.strftime("%Y-%m")
                category = text.strip()

    return category.title(), month