"""
File: onboarding_flow.py
Author: Vasu Chukka
Created: 2025-04-27
Last Modified: 2025-04-28
Description:
    FinSense Agent User Onboarding Flow
    - Collects salary, rent, internet, electricity, and other fixed costs
    - Validates numeric entries
    - Saves user profile to JSON for future use
    - Greets user naturally
"""

import os
import json

# --------------------------------------------
# 📂 Where the user profile is stored
# --------------------------------------------
USER_PROFILE_PATH = "data/user_profiles/default_profile.json"

#---------------------------------
# Helper function to load user profile
#---------------------------------
def load_user_profile() -> dict:
    """
    Loads the saved user profile from JSON.

    Returns:
        dict: User profile data or empty dict if not found.
    """
    if os.path.exists(USER_PROFILE_PATH):
        try:
            with open(USER_PROFILE_PATH, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    else:
        return {}

#---------------------------------
# Helper function to ask for numeric input
#---------------------------------
def _ask_numeric(prompt: str) -> float:
    """Prompt until the user enters a valid number."""
    while True:
        val = input(prompt).strip()
        try:
            return float(val)
        except ValueError:
            print("⚠️  Please enter a numeric value (e.g. 395 or 27.5).")

# --------------------------------------------
# 🧠 Onboarding Conversation Flow
# --------------------------------------------
def onboarding_conversation():
    print("👩‍💼 FinSense Agent:")
    print("Hey there! 👋 Welcome to FinSense, your personal budgeting assistant.")
    print("Let's set up your basic monthly profile first.\n")

    salary = _ask_numeric("💬 What's your average monthly take-home salary (after taxes)? → €")
    print(f"✅ Got it — €{salary} monthly income.\n")

    rent = _ask_numeric("🏠 What's your monthly rent (include heating & water)? → €")
    print(f"✅ Noted — €{rent} for rent & utilities.\n")

    internet = _ask_numeric("📡 What's your monthly Internet/WiFi bill? → €")
    print(f"✅ Internet cost recorded — €{internet}.\n")

    electricity = _ask_numeric("⚡ What's your average monthly electricity bill? → €")
    print(f"✅ Electricity cost recorded — €{electricity}.\n")

    fixed_costs = []
    while True:
        more = input("💬 Do you have other fixed costs (gym, phone, subscriptions, EMIs)? (yes/no) → ").strip().lower()
        if more in ("no", "n"):
            break
        if more not in ("yes", "y"):
            print("⚠️  Please answer 'yes' or 'no'.")
            continue

        desc = input("➕ Name of the fixed cost (e.g. Gym, Phone Bill): → ").strip()
        amt = _ask_numeric(f"💶 How much is {desc} per month? → €")
        fixed_costs.append({"description": desc, "amount": amt})
        print(f"✅ Added: {desc} — €{amt}\n")

    # Build profile
    profile = {
        "salary": salary,
        "rent": rent,
        "internet": internet,
        "electricity": electricity,
        "other_fixed_costs": fixed_costs
    }

    # Save to disk
    os.makedirs("data/user_profiles", exist_ok=True)
    profile_path = "data/user_profiles/default_profile.json"
    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)

    # Summary
    print("\n🎉 Setup Complete! Here's your profile summary:\n")
    print(f"💵 Salary: €{salary}")
    print(f"🏠 Rent & Utilities: €{rent}")
    print(f"📡 Internet: €{internet}")
    print(f"⚡ Electricity: €{electricity}")
    if fixed_costs:
        print("📋 Other Fixed Costs:")
        for i, fc in enumerate(fixed_costs, 1):
            print(f"   {i}. {fc['description']}: €{fc['amount']}")
    else:
        print("📋 No additional fixed costs provided.")
    print("\n✅ Your profile has been saved for future use.")
    print("🌟 Welcome aboard FinSense! Ready to take control of your budget. 🚀\n")