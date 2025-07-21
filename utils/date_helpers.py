from datetime import datetime, timedelta
import re
import calendar
from typing import Tuple


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
            if len(a) == 4:
                year, mon = a, b
            else:
                mon, year = a, b
            month = f"{year}-{mon}"
            category = lowered.replace(token, "").strip()
            category = re.sub(r"\b(in|on)\b", "", category).strip()

        else:
            # 3) Full month names with optional year
            m = re.search(
                r"(january|february|march|april|may|june|july|"
                r"august|september|october|november|december)"
                r"(?:\s+(\d{4}))?",
                lowered,
                re.IGNORECASE
            )
            if m:
                month_name = m.group(1).lower()
                year = m.group(2) or str(now.year)
                month_map = {name: f"{idx:02d}" for idx, name in enumerate(calendar.month_name) if idx}
                month = f"{year}-{month_map[month_name]}"
                category = re.sub(rf"\b(in\s*)?{month_name}\b(?:\s+\d{{4}})?", "", lowered).strip()
            else:
                # 4) Three-letter abbreviations
                month = None
                category = lowered
                for idx, abbr in enumerate(calendar.month_abbr):
                    if idx == 0:
                        continue
                    if re.search(rf"\b{abbr.lower()}\b", lowered):
                        month = f"{now.year}-{idx:02d}"
                        category = re.sub(rf"\b(in\s*)?{abbr.lower()}\b", "", lowered).strip()
                        break

                if month is None:
                    month = now.strftime("%Y-%m")
                    category = text.strip()

    return category.title(), month