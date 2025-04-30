# 📊 FinSense - Intelligent Personal Finance Agent

The **BudgetingAgent** is the first modular agent in the FinSense AI project. It is designed using the GAME framework and follows principles of Agent2Agent communication and Model Context Protocol (MCP). This agent helps manage your personal monthly budget, enforce discipline through the 50/30/20 rule, and guide you toward your financial goals.

---

Built with:

- ✅ GAME Framework
- ✅ FastAPI + Uvicorn server
- ✅ Native Notion webhook integration
- ✅ LLM-powered budget parser
- ✅ PDF bank statement import
- ✅ 50/30/20 budgeting logic
- ✅ Notion sync and real-time webhooks

---

## 🎯 Core Purpose
Help you:
- Track daily and monthly spending
- Stay within a personalized budget using the 50/30/20 rule
- Receive alerts, summaries, and planning suggestions
- Ask questions like "How much did I spend on Food in March?"

---

## ✅ Supported Use Cases

### 🔹 Basic Functions (MVP)
1. **Parse PDF bank statements** to build a transaction history  
2. **Read expenses from Notion** (manual entries or synced data)  
3. **Apply 50/30/20 budget rule** against monthly income  
4. **Alert if over budget** in Needs, Wants, or Savings  
5. **Summarize remaining budget** by category  
6. **Natural language summaries** (e.g., “Give me my March spending”)

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

## 🧠 Key Architecture Concepts

| Concept | Description |
|--------|-------------|
| Goals | Built using the GAME framework (Goal → Actions → Memory → Env) |
| Tools | Actions are registered with schemas and decorators |
| Memory | Stores transaction history, summaries, and agent context |
| Environment | Executes tools safely and tracks context |
| Agent2Agent | Future-ready to communicate with other agents like InvestmentAgent |

---

## 🔧 Data Sources

- 📄 PDF Statements (Parsed & Categorized) → Imported using `pdfplumber`
- 📟 Notion Database → Synced and merged
- 🗨 User Questions → Routed through LLM parser or CLI input

---

## 🔄 Outputs
- CLI or Notion output
- 🧠 Budget summaries (daily, monthly)
- 🗂 Category breakdowns
- 💬 Agent chat-style messages: “You're 15% over budget for Wants”

---

## 🚫 Not In Scope (for now)
- Real-time bank syncing (uses manual PDFs)
- Multi-user support
- Currency conversion
- Machine learning classification (uses rules + LLM fallback)

---

## 🛠 Future-Ready
This agent is designed to grow over time by:
- Adding new tools ("predict next month's spend")
- Registering new goals ("Save €200 for vacation")
- Adding richer interfaces (mobile, voice, etc.)

---

---

## ⚙️ Setup Instructions

### 1. Clone the repo and create environment

```bash
git clone https://github.com/your-username/finsense.git
cd finsense
conda create -n finsense python=3.11
conda activate finsense
```

### 2. Install requirements

```bash
pip install -r requirements.txt
```

Or use the safer fallback installer:

```bash
python install_requirements_safely.py
```

### 3. Start FastAPI webhook server

```bash
uvicorn server.main:app --reload --port 8000
```

### 4. Expose with ngrok

```bash
ngrok http 8000
```

Paste the resulting URL into Notion Developer Dashboard as your webhook endpoint.

---

## 🦡 Native Notion Webhooks

You can register your webhook URL at [notion.so/my-integrations](https://www.notion.so/my-integrations) to receive events like:

- `page.created`
- `page.updated`
- `comment.created`

FinSense reacts to these events automatically:
- Parses new transactions
- Replies to user queries
- Logs budget changes

---

## 🧪 Testing Webhooks

Use curl or Postman:

```bash
curl -X POST https://your-ngrok-url.ngrok-free.app/notion-webhook/ \
  -H "Content-Type: application/json" \
  -d '{"type": "page.created", "data": { ... }}'
```

You’ll see live logs in the FastAPI server console.

---

## 🔐 Webhook Signature (Optional)

Enable HMAC verification for security.

1. Set in your Notion webhook settings
2. Add it to your `.env`:

```env
NOTION_WEBHOOK_SECRET=your-secret-here
```

---

## 📁 Project Structure

```
finsense/
├── cli/                    ← Command-line interaction
├── server/                 ← FastAPI app and webhook handlers
│   └── notion_webhook.py
├── tools/                  ← Budgeting tools, summarizers
├── utils/                  ← Notion sync, helper functions
├── data/                   ← Persistent storage (transactions, profile)
├── requirements.txt
```

---

## 🧠 FinSense Chat (Coming Soon)

Notion-based conversational chat UI:

- User adds question in a Notion database
- FinSense agent responds in the same table
- Acts like a chat between you and your budget coach

---

## 📈 Future Roadmap

- Pie chart exports for monthly summaries
- InvestmentAgent & GoalPlannerAgent
- Multi-device support
- Richer report generation in Notion

---

## 👨‍💼 Author

Built by Vasu Chukka  
📬 Email: vasu.chukka@outlook.com  
💻 GitHub: [github.com/vasuchukka](https://github.com/vasuchukka)

Stay focused. Stay frugal. Let your agent do the math. 💸

