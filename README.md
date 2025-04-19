# 📊 BudgetingAgent (FinSense AI)

The **BudgetingAgent** is the first modular agent in the FinSense AI project. It is designed using the GAME framework and follows principles of Agent2Agent communication and Model Context Protocol (MCP). This agent helps manage your personal monthly budget, enforce discipline through the 50/30/20 rule, and guide you toward your financial goals.

---

## 🎯 Core Purpose
Help you:
- Track daily and monthly spending
- Stay within a personalized budget using the 50/30/20 rule
- Receive alerts, summaries, and planning suggestions

---

## ✅ Supported Use Cases

### 🔹 Basic Functions (MVP)
1. **Analyze PDF bank statements** to build a spending history
2. **Read expenses from Notion** (manual daily logging)
3. **Apply 50/30/20 budgeting rule** on defined income
4. **Alert when over budget** in any category (Needs, Wants, Savings)
5. **Report remaining balance** in each category ("€50 left for Eating Out")
6. **Summarize budget health** daily, weekly, and monthly

### 🔹 Advanced Functions (Phase 2)
7. **Generate a standardized monthly report** with:
   - Category breakdown (pie chart or table)
   - Over/under budget indicators
   - Total vs actual vs planned spending

8. **Compare spending with past months** to show trends
   - “You're spending 20% more on subscriptions than last month”

9. **Handle user affirmations / short-term goals**
   - “I want to buy €100 sneakers this week” → Suggest where to cut costs

10. **Guide user planning with tips and trade-offs**
   - Show impact of optional purchases, offer suggestions to rebalance budget

---

## 🔧 Data Sources
- **PDF Bank Statements** → Parsed and categorized
- **Notion Database** → Manually entered daily expenses
- **User Prompts** → Questions like "How much did I spend on food this month?"

---

## 🧠 Key Concepts
- **Goals:** Modular and extensible using the GAME pattern
- **Actions:** Registered with schemas and decorators
- **Memory:** Stores conversation history and past summaries
- **Environment:** Executes budgeting tools in safe, traceable format
- **Agent2Agent Ready:** Can communicate with InvestmentAgent or DecisionAgent later

---

## 🔄 Outputs
- CLI or Streamlit output
- Budget breakdowns (text, JSON, pie chart)
- Natural language reports: “You're 15% over budget for Wants”
- Advice: "Skip eating out twice this week to stay under budget."

---

## 🚫 Not In Scope (for now)
- Multi-user tracking
- Real-time bank syncing
- Currency conversion
- Machine learning categorization (currently rule-based)

---

## 🛠 Future-Ready
This agent is designed to grow over time by:
- Adding new tools ("predict next month's spend")
- Registering new goals ("Save €200 for vacation")
- Adding richer interfaces (mobile, voice, etc.)

---

Stay focused. Stay frugal. Let your agent do the math. 💸

