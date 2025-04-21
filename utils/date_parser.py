# import dateparser
# from datetime import datetime

# def normalize_date(date_str: str) -> str:
#     """
#     Converts natural language date strings like 'today', 'next Monday'
#     into YYYY-MM-DD format.
#     """
#     parsed = dateparser.parse(date_str)

#     if not parsed:
#         raise ValueError(f"Could not parse date from '{date_str}'")

#     return parsed.strftime("%Y-%m-%d")
