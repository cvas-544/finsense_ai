#!/usr/bin/env python3
"""
Module: query_parser.py
Location: utils/query_parser.py
Author: Vasu Chukka
Created: 2025-05-01
Last Modified: 2025-05-01

Description:
    Uses OpenAI function-calling to parse budget queries into structured arguments.
"""
import os
import re
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Initialize LLM client
load_dotenv()
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Function schema
parse_budget_query_def = {
    "name": "parse_budget_query",
    "description": (
        "Extracts 'category' and 'month' (YYYY-MM) from a natural-language budget query. "
        "Returns a JSON object with exactly two keys: category (Title-cased) and month."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "The normalized category name (e.g., 'Food', 'Entertainment', 'All')."
            },
            "month": {
                "type": "string",
                "pattern": "^\\d{4}-\\d{2}$",
                "description": "Month in ISO format YYYY-MM. If user said 'last month' or omitted, handle appropriately."
            }
        },
        "required": ["category", "month"],
        "additionalProperties": False
    }
}

# System prompt
parse_system_prompt = '''
You are a budget-query parser. Given a user's question about spending or budget,
extract and return a JSON object with exactly two fields: "category" and "month".
- "category" must be a title-cased category name or "All" if it refers to overall spending.
- "month" must be in YYYY-MM format, interpreting "last month" or full month names correctly.
Return only the function_call in JSON (no extra text).
'''

def call_parse_budget_query(user_input: str) -> dict:
    """
    Parses a natural-language budget query into structured {category, month} output.

    - Sends user input to LLM (function-calling with parse_budget_query schema).
    - Extracts the target category and month (YYYY-MM format) from LLM response.
    - If the user specifies a month without a year (e.g., "January"), 
    defaults the year to the current system year.
    - If the month or year information is missing or malformed, defaults to current month.
    - Handles relative phrases like "last month" and "this month" correctly.

    Args:
        user_input (str):
            The natural-language query provided by the user.

    Returns:
        dict:
            {
                "category": str,  # normalized to Title Case
                "month": str,     # normalized to YYYY-MM format
            }
    """
    response = llm_client.chat.completions.create(
        model="gpt-4-0613",
        messages=[
            {"role": "system", "content": parse_system_prompt},
            {"role": "user", "content": user_input}
        ],
        functions=[parse_budget_query_def],
        function_call={"name": "parse_budget_query"}
    )

    func_call = response.choices[0].message.function_call
    raw_args = func_call.arguments

    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
    except Exception:
        args = {}

    category = args.get("category", "All").strip().title()
    month = args.get("month")

    # 📅 New year handling logic
    if not month or not re.match(r"^\d{4}-\d{2}$", month):
        month = datetime.now().strftime("%Y-%m")
    else:
        # If month extracted but year missing (e.g., "01" instead of "2025-01")
        if re.match(r"^\d{2}$", month[-2:]):
            month = f"{datetime.now().year}-{month[-2:]}"

    return {"category": category, "month": month}
