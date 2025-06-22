import json
import os

CATEGORY_FILE = os.path.join("data", "category_groups.json")

def load_category_groups():
    """
    Loads category groupings (e.g., 'Food' → ['Groceries', 'Restaurants'])

    Returns:
        Dict[str, List[str]]: category → expanded list
    """
    try:
        with open(CATEGORY_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Could not load category groups: {e}")
        return {}