from typing import List, Tuple
from utils.db_connection import get_db_connection

def load_expense_income_keywords() -> Tuple[List[str], List[str]]:
    """
    Loads expense and income keywords from the RDS table `expense_income_keywords`.

    Returns:
        Tuple[List[str], List[str]]: expense_keywords, income_keywords
    """
    expense_keywords = []
    income_keywords = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT keyword, category FROM expense_income_keywords")
        rows = cur.fetchall()
        for keyword, category in rows:
            if category == "expense":
                expense_keywords.append(keyword.lower())
            elif category == "income":
                income_keywords.append(keyword.lower())
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Failed to load expense/income keywords from DB: {e}")
    
    return expense_keywords, income_keywords