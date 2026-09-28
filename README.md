# Aria — AI Multi-Agent Customer Support System

A full-stack customer support platform with four interconnected AI agents, a customer
dashboard, and an admin dashboard, built on React + Tailwind CSS, Flask, and MongoDB.

## Architecture

```
support-system/
├── backend/                 Flask API + AI agents + MongoDB access
│   ├── app.py                Flask app factory / entry point
│   ├── config.py              Env-driven configuration
│   ├── extensions.py          Mongo client, JWT manager, indexes
│   ├── seed.py                 Optional: demo customer/orders/FAQs
│   ├── agents/
│   │   ├── base_agent.py       Shared Anthropic API call wrapper
│   │   ├── knowledge_base.py    TF-IDF RAG retrieval over FAQ collection
│   │   ├── query_agent.py       Agent 1: intent detection + RAG FAQ answering
│   │   ├── order_agent.py       Agent 2: order lookup/tracking/cancellation
│   │   ├── complaint_agent.py   Agent 3: ticket creation, categorization, priority
│   │   ├── sentiment_agent.py   Agent 4: sentiment/urgency + auto-escalation
│   │   └── orchestrator.py      Routes every message across the 4 agents dynamically
│   ├── models/                 MongoDB collection access (users, orders, tickets,
│   │                            conversations/messages, feedback, faqs)
│   └── routes/                 REST endpoints (auth, profile, chat, orders, tickets,
│                                feedback, admin)
└── frontend/                 React + Tailwind SPA
    └── src/
        ├── api/client.js        Axios instance with JWT injection
        ├── context/AuthContext.jsx
        ├── components/          Layout, route guard, status badges
        └── pages/
            ├── customer/         Dashboard, Chat, Orders, Tickets, Feedback, Profile
            └── admin/            Overview/analytics, Customers, Orders, Tickets,
                                   Conversations monitor, Knowledge base
```

## How the 4 agents connect

Every chat message goes through `agents/orchestrator.py`:

1. **Sentiment & Escalation Agent** scores sentiment/urgency on *every* message.
2. **Query Agent** classifies intent (`faq_question`, `order_status`, `order_cancel`,
   `complaint`, `ticket_status`, `human_handoff`, …) using the LLM.
3. Based on intent, the orchestrator dynamically routes to:
   - **Order Management Agent** — reads real order documents from MongoDB, checks the
     cancellation-eligibility window/status, and cancels or explains why it can't.
   - **Complaint & Ticket Agent** — classifies category/priority with the LLM and
     writes a real ticket document.
   - **Query Agent** — retrieves the top matching FAQ articles via TF-IDF cosine
     similarity (RAG) from the admin-managed `faqs` collection and answers using them
     plus conversation history.
4. If sentiment/urgency crosses the configured threshold (see `config.py`), the
   **Sentiment Agent** escalates the customer's open ticket automatically — this also
   happens mid-conversation, not just at ticket creation.
5. Every turn is persisted to `conversations` / `messages`, so history carries across
   the whole chat and is visible to admins in real time.

Nothing is hardcoded: FAQ answers, order data, ticket categorization/priority, and
sentiment scores are all produced live by the LLM reasoning over real MongoDB data.

## Setup

### Prerequisites
- Python 3.10+
- Node 18+
- A running MongoDB instance (local `mongod`, or a MongoDB Atlas connection string)
- An Anthropic API key (for the 4 AI agents)

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set MONGO_URI, ANTHROPIC_API_KEY, JWT_SECRET_KEY, ADMIN_EMAIL/PASSWORD

python seed.py                  # optional: creates a demo customer + orders + FAQs
python app.py                   # runs on http://localhost:5000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                     # runs on http://localhost:5173, proxies /api to :5000
```

### 3. Log in

- **Admin**: the email/password from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`
  (an admin account is auto-created on first backend boot).
- **Customer**: register a new account from the UI, or use the seeded demo account
  (`demo@customer.local` / `Demo1234!`) if you ran `seed.py`.

## Notes on production deployment

- Set `FLASK_ENV=production`, run via `gunicorn -w 4 app:app`, and put it behind a
  reverse proxy (nginx) with HTTPS.
- Build the frontend with `npm run build` and serve `frontend/dist` as static files
  (or host it separately and point `CORS_ORIGIN` at that origin).
- Use a managed MongoDB (Atlas) with authentication enabled, and rotate
  `JWT_SECRET_KEY` / `ANTHROPIC_API_KEY` via your platform's secret manager rather than
  a committed `.env` file.
- The Sentiment Agent's escalation thresholds and the order cancellation window are
  both configurable in `backend/config.py`.
