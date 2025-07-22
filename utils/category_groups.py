from typing import Dict, List
from collections import defaultdict
from utils.db_connection import get_db_connection

def load_merged_category_groups(user_id: str) -> Dict[str, List[str]]:
    """
    Loads and merges category group keyword mappings from:
    - Global table: global_category_groups (group_name → categories[])
    - User table: user_category_keywords (user_id, group_name, keyword)

    Returns:
        A dictionary where group_name maps to a list of unique keywords.
    """
    merged = defaultdict(set)

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Load global group mappings
        cur.execute("SELECT group_name, categories FROM global_category_groups")
        for group_name, categories in cur.fetchall():
            for keyword in categories:
                merged[group_name].add(keyword.lower())

        # Load user-specific keywords
        cur.execute("""
            SELECT group_name, keyword FROM user_category_keywords
            WHERE user_id = %s
        """, (user_id,))
        for group_name, keyword in cur.fetchall():
            merged[group_name].add(keyword.lower())

        cur.close()
        conn.close()

    except Exception as e:
        print(f"⚠️ Error loading category groups: {e}")

    # Convert sets to sorted lists
    return {group: sorted(list(keywords)) for group, keywords in merged.items()}