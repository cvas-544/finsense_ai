# 📊 FinSense - Intelligent Personal Finance Agent

The **BudgetingAgent** is the first modular agent in the FinSense AI project. It is designed using the GAME framework and follows principles of Agent2Agent communication and Model Context Protocol (MCP). This agent helps manage your personal monthly budget, enforce discipline through the 50/30/20 rule, and guide you toward your financial goals.

---

## ✅ Built With:
	- GAME Framework (Goal → Actions → Memory → Env)
	- PostgreSQL (via AWS RDS)
	- Python 3.11+
	- OpenAI API for smart categorization
	- pdfplumber for bank statement parsing
	- Telegram Bot for interaction
	- EC2-hosted CLI/API runtime (optional)

---

## 🎯 What Can It Do?
	- Parse bank statement PDFs into structured transactions
	- Categorize and label spending using keywords + LLM fallback
	- Automatically assign Needs/Wants/Savings type
	- Enforce a 50/30/20 budget rule based on income
	- Summarize expenses monthly or by category
	- Answer natural language questions like:
	- “How much did I spend on groceries in April?”
	- “What’s my remaining Wants budget for June?”

---

## ✅ Supported Features

## 📄 PDF Import
	- Extracts date, description, and amount from PDF lines
	- Auto-categorizes using user-defined + global keywords
	- Applies income/expense sign logic
	- Saves all transactions to AWS RDS (PostgreSQL)
	- Skips duplicates based on (date, description, amount)

## 🤖 Auto Categorization
	- Runs keyword match across global/user keyword tables
	- Falls back to LLM if no match found
	- Prompts user to approve or adjust the categorization
	- Updates transaction type (Needs/Wants/Savings) accordingly

## 📊 Budget Summarization
	- Uses income and preferred ratio from user_profile table
	- Applies 50/30/20 rule to evaluate spending limits
	- Compares actual spending to budgeted goals
	- Supports summaries by category or overall budget

---

## 🧠 Key Architecture Concepts

| Concept | Description |
|--------|-------------|
| Goals | Built using the GAME framework (Goal → Actions → Memory → Env) |
| Tools | Actions are registered with schemas and decorators |
| Memory | Stores transaction history, summaries, and agent context |
| Environment | Executes tools safely and tracks context |
| Agent2Agent | Future-ready to communicate with other agents like InvestmentAgent |
| RDS Backend | All data stored in PostgreSQL on AWS RDS |
| Telegram UI | Bot interface for real-time queries and commands |
| EC2 Hosting | Deploy the CLI and tools API on AWS EC2 instance for persistent access |

---

## 🚫 Not In Scope (for now)
- Real-time bank syncing (uses manual PDFs)
- Currency conversion
- Investment tools (coming later)
- Visual dashboards (basic summaries only for now)

---

## 🛠 Future-Ready
This agent is designed to grow over time by:
- Adding new tools ("predict next month's spend")
- Registering new goals ("Save €200 for vacation")
- Adding richer interfaces (mobile, voice, etc.)

---

## 👨‍💼 Author

Built by Vasu Chukka  
📬 Email: vasu.chukka@outlook.com  
💻 LinkedIn: [VasuChukka](https://www.linkedin.com/in/vasu-chukka-1a3569116/)

Let your agent handle your budget while you live your life. 💸

