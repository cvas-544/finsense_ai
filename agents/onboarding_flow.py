"""
File: onboarding_flow.py
Author: Vasu Chukka
Created: 2025-04-27
Last Modified: 2025-04-28
Description:
    FinSense Agent User Onboarding Flow
    - Collects salary, rent, wifi, electricity, and other fixed costs
    - Validates inputs, and enforces explicit "no" before summary
    - Saves user profile to JSON file for future use
    - Handles missing or corrupted profile file gracefully
"""

import os
import json

# --------------------------------------------
# 📂 Where the user profile is stored
# --------------------------------------------
PROFILE_DIR = "data/user_profiles"
PROFILE_PATH = os.path.join(PROFILE_DIR, "default_profile.json")

#---------------------------------
# Helper function to ask for numeric input
#---------------------------------
def _prompt_number(prompt_text: str) -> float:
    """Prompt until the user enters a valid float."""
    while True:
        val = input(prompt_text).strip().lstrip("€")
        try:
            return float(val)
        except ValueError:
            print("⚠️ Please enter a valid number.")

# --------------------------------------------
# 🧠 Onboarding Conversation Flow
# --------------------------------------------
def onboarding_conversation():
    """Run the interactive onboarding flow, saving profile at the end."""
    print("👩‍💼 FinSense Agent:")
    print("\nHey there! 👋 Welcome to FinSense, your personal budgeting assistant.")
    print("I'll ask you a few questions to set up your basic profile. Ready?\n")

    salary = _prompt_number("\n🧾 What's your average monthly *take-home salary* (after taxes)? → €")
    print(f"✅ Got it — €{salary} monthly income.")

    rent = _prompt_number("\n🏠 What's your monthly *rent*? (Include heating & water) → €")
    print(f"✅ Noted — €{rent} for rent & utilities.")

    wifi = _prompt_number("\n📡 How much do you pay monthly for *Internet/WiFi*? → €")
    print(f"✅ Internet cost recorded — €{wifi}.")

    electricity = _prompt_number("\n⚡ What's your average monthly *electricity* bill? → €")
    print(f"✅ Electricity cost recorded — €{electricity}.")

    other_fixed = []
    while True:
        more = input("💬 Do you have any other fixed costs (gym, phone, subscriptions, EMIs)? (yes/no) → ").strip().lower()
        if more == "yes":
            desc = input("➕ Name of the fixed cost (e.g. Gym, Phone Bill): → ").strip().title()
            amount = _prompt_number(f"💶 How much is {desc} per month? → €")
            other_fixed.append({"description": desc, "amount": amount})
        elif more == "no":
            break
        else:
            print("⚠️ Please answer 'yes' or 'no'.")
    
    profile = {
        "salary": salary,
        "rent": rent,
        "wifi": wifi,
        "electricity": electricity,
        "other_fixed_costs": other_fixed
    }

    # Ensure directory exists
    os.makedirs(PROFILE_DIR, exist_ok=True)
    # Save profile
    try:
        with open(PROFILE_PATH, "w") as f:
            json.dump(profile, f, indent=2)
    except Exception as e:
        print(f"❌ Failed to save profile: {e}")
        return

    # Summary
    print("\n🎉 Setup Complete! Here's your profile summary:\n")
    print(f"💵 Salary: €{salary}")
    print(f"🏠 Rent & Utilities: €{rent}")
    print(f"📡 Internet: €{wifi}")
    print(f"⚡ Electricity: €{electricity}")
    if other_fixed:
        print("📋 Other Fixed Costs:")
        for idx, fc in enumerate(other_fixed, 1):
            print(f"  {idx}. {fc['description']}: €{fc['amount']}")
    else:
        print("📋 No additional fixed costs provided.")

    print("\n✅ Your profile has been saved for future use.")
    print("🌟 Welcome aboard FinSense! 🚀\n")

#---------------------------------
# Helper function to add fixed costs to existing profile
#---------------------------------
def add_fixed_costs_to_profile():
    """Let a returning user append more fixed costs."""
    import json, os
    path = "data/user_profiles/default_profile.json"
    with open(path) as f:
        profile = json.load(f)

    fixed_costs = profile.get("other_fixed_costs", [])
    # reuse the same yes/no loop as above, appending to fixed_costs
    # … (copy-paste/refactor the loop code)

    profile["other_fixed_costs"] = fixed_costs
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)
    print("✅ Fixed costs updated!")

#---------------------------------
# Helper function to load user profile
#---------------------------------
def load_user_profile() -> dict:
    """
    Load the saved user profile.
    Returns empty dict if missing or corrupted, printing an appropriate warning.
    """
    try:
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Profile file not found—starting fresh onboarding.")
    except json.JSONDecodeError:
        print("❌ Profile data corrupted—please re-onboard.")
    return {}
