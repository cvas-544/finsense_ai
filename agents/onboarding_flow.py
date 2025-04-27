"""
File: onboarding_flow.py
Author: Vasu Chukka
Created: 2025-04-27
Last Modified: 2025-04-27
Description:
    FinSense Agent User Onboarding Flow
    - Collects salary, rent, wifi, groceries, and other fixed costs
    - Saves user profile to JSON file for future use
    - Greets user naturally
"""

import os
import json

# --------------------------------------------
# 📂 Where the user profile is stored
# --------------------------------------------
USER_PROFILE_PATH = "data/user_profile.json"

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

# --------------------------------------------
# 🧠 Onboarding Conversation Flow
# --------------------------------------------
def onboarding_conversation() -> dict:
    print("\n👋 Welcome to FinSense! Let's quickly set up your financial profile.\n")
    profile = {}

    # Mandatory fixed costs
    try:
        profile["salary"] = float(input("💬 What is your monthly salary (in euros)? "))
        profile["rent"] = float(input("🏠 How much is your monthly rent (in euros)? (include heating, water) "))
        profile["wifi"] = float(input("🌐 What is your monthly WiFi/Internet bill (in euros)? "))
        profile["electricity"] = float(input("⚡ What is your average monthly electricity bill (in euros)? "))
    except ValueError:
        print("⚠️ Please enter numeric values. Let's restart later.")
        return {}

    # Optional recurring fixed costs
    profile["fixed_costs"] = []

    add_more = input("\n💬 Do you have any additional fixed costs like gym, phone, subscriptions? (yes/no): ").strip().lower()
    while add_more == "yes":
        name = input("➕ What is the name of the fixed cost? (e.g., Gym, Phone Bill, Netflix): ").strip()
        try:
            amount = float(input(f"💶 How much is the monthly amount for {name} (in euros)? "))
        except ValueError:
            print("⚠️ Please enter a valid number for amount. Skipping this item.")
            continue

        profile["fixed_costs"].append({"name": name, "amount": amount})

        add_more = input("\n💬 Any more fixed costs to add? (yes/no): ").strip().lower()

    # Save profile
    os.makedirs("data", exist_ok=True)
    with open(USER_PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)

    print("\n✅ Your financial profile has been saved successfully!")
    print("🎯 FinSense is now ready to assist you with personalized budgeting and insights.\n")

    return profile