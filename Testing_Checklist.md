# 📦 FinSense Deployment Checklist

Use this before launching to production (via EC2):

---

## 🔪 Unit Tests (Each Tool)

* [x] parse\_bank\_pdf(): Correctly parses dates, amounts, and descriptions
* [x] auto\_categorize\_transactions(): Assigns category from keyword or LLM
* [x] categorize\_transactions(): 
* [x] summarize\_budget(): Enforces 50/30/20 rule with accurate totals
* [x] summarize\_income(): Gives the summary of the incomes
* [x] record\_transaction(): Stores entries, validates category/type
* [x] update\_transaction(): Allows user-initiated edits
* [x] summarize\_category\_spending(): Correct filtering by category/month
* [x] query\_category\_spending(): Parses NL queries to valid outputs
* [x] add\_user\_category\_keyword():
* [x] record\_income\_source():
* [x] categorize\_transactions():
* [-] terminate():

> 📂 test files located in: utils/test\_\*.py

---

## 🔗 Integration Tests (End-to-End)

* [x] Upload sample PDF and confirm 15+ transactions are parsed
* [ ] All transactions are auto-categorized, no Uncategorized remains
* [ ] summarize\_budget() shows accurate distribution
* [ ] summarize\_category\_spending() gives correct numbers
* [ ] LLM fallback responds to unknown descriptions
* [ ] Invalid PDF or empty file returns proper warning
* [ ] update\_transaction() successfully modifies a row
* [ ] record\_income\_source() reflects in summary

---

## 🔐 Environment & Secrets

* [ ] .env file present with valid:

  * [ ] DB\_HOST, DB\_USER, DB\_PASSWORD, DB\_NAME
  * [ ] OPENAI\_API\_KEY
  * [ ] TELEGRAM\_BOT\_TOKEN
* [ ] .env is listed in .gitignore
* [ ] No hardcoded passwords/API keys in any .py file

---

## 📙 Database Integrity

* [ ] All UUIDs valid and unique
* [ ] transactions.type ∈ {Needs, Wants, Savings}
* [ ] category\_type\_mapping includes “Other” with valid budget\_type
* [ ] All transactions have valid user\_id from user\_profile
* [ ] amount sign logic (– for expense, + for income/savings)

---

## 📲 Telegram Bot

* [ ] Telegram bot is running with:

  * [ ] /start responds
  * [ ] Uploading PDF file triggers auto parsing
  * [ ] User can ask “How much did I spend on groceries in July?”
* [ ] Auto-categorize triggers via CLI and bot
* [ ] Bot doesn’t crash on invalid files/text

---

## 🚀 Server Readiness (EC2)

* [ ] EC2 instance running and secure (SSH key, firewall open for port 8000)
* [ ] PostgreSQL RDS credentials reachable from EC2
* [ ] FastAPI server runs and responds to basic GET / POST
* [ ] Uvicorn server handles file uploads, categorization smoothly
* [ ] Data/ folder does not include real PDFs or PII (empty)

---

## 📊 Optional Dashboard Prep

* [ ] Pie chart function working
* [ ] Spending summary per category, per month
* [ ] Monthly report template rendering correctly (markdown or chart output)

---

## 📅 Final Step

* [ ] Push final commit to GitHub
* [ ] Tag release version (e.g., v0.5-mvp-ec2)
* [ ] Announce internal test availability
