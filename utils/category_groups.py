import psycopg2
from typing import Dict, List
from utils.db_connection import get_db_connection

def load_merged_category_groups(user_id: str) -> Dict[str, List[str]]:
    """
    Loads the merged category group mappings from:
    - global_category_groups (shared across all users)
    - user_category_overrides (user-defined overrides that append or replace keywords)

    Returns:
        A dictionary where each group_name maps to a list of keywords.
    """
    merged: Dict[str, List[str]] = {}

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Load global mappings
        cur.execute("SELECT group_name, categories FROM global_category_groups")
        for group_name, categories in cur.fetchall():
            merged[group_name] = list(set(merged.get(group_name, []) + categories))

        # Load user-specific overrides (which append to the global)
        cur.execute("""
            SELECT group_name, categories
            FROM user_category_overrides
            WHERE user_id = %s
        """, (user_id,))
        for group_name, categories in cur.fetchall():
            merged[group_name] = list(set(merged.get(group_name, []) + categories))

        cur.close()
        conn.close()

    except Exception as e:
        print(f"⚠️ Error loading category groups: {e}")

    return merged