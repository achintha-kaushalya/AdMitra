# AdMitra — AI-Powered Digital Marketing Automation

> **IT3041 — Information Retrieval and Web Analytics**
> SLIIT, Sri Lanka | Group Project

AdMitra is a **multi-agent AI system** that automates digital marketing analysis using Google Gemini 1.5 Flash, FastAPI, ChromaDB, and Streamlit.

---

## 🏗️ Architecture

```
Streamlit Dashboard  ─── HTTP ──▶  FastAPI Orchestrator
                                        │
                     ┌──────────────────┼──────────────────────┐
                     ▼                  ▼                       ▼
             DiagnosticAgent   PerformanceAgent           BudgetAgent
                                        │                       │
                                   ChromaDB (RAG) ◀────────────┘
                     ▼                  
             ContentAgent     EngagementAgent
             (Gemini LLM)     (HuggingFace + spaCy + Gemini)
```

## 👥 Team & Roles

| Member | Role | Branch | Owns |
| :--- | :--- | :--- | :--- |
| Member 1 | Backend Lead & Repo Admin | `feature/orchestrator-security` | `shared/`, `orchestrator/main.py`, repo setup |
| Member 2 | AI Agents Lead | `feature/diagnostic-performance-agents` | `agents/diagnostic_agent.py`, `agents/performance_agent.py` |
| Member 3 | IR & Data Lead | `feature/vector-store`, `feature/budget-agent` | `ir/vector_store.py`, `agents/budget_agent.py` |
| Member 4 | Frontend & NLP Lead | `feature/content-engagement`, `feature/frontend-dashboard` | `agents/content_agent.py`, `agents/engagement_agent.py`, `frontend/dashboard.py` |

---

## ⚡ Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/<your-org>/AdMitra.git
cd AdMitra
git checkout development
```

### 2. Create & Activate Virtual Environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install spaCy Language Model
```bash
python -m spacy download en_core_web_sm
```

### 5. Configure Environment
```bash
cp .env.example .env
# Edit .env and fill in:
#   GOOGLE_API_KEY  — from https://aistudio.google.com/app/apikey
#   FERNET_KEY      — generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 6. Run the FastAPI Orchestrator
```bash
uvicorn orchestrator.main:app --reload --port 8000
```
Open: http://localhost:8000/docs (auto-generated Swagger UI)

### 7. Run the Streamlit Dashboard (separate terminal)
```bash
streamlit run frontend/dashboard.py
```

---

## 🗂️ Folder Structure

```
AdMitra/
├── orchestrator/
│   └── main.py                # FastAPI — routes requests to agents
├── agents/
│   ├── diagnostic_agent.py    # Rule-based ad account health checker
│   ├── performance_agent.py   # LLM + RAG campaign performance analysis
│   ├── budget_agent.py        # LLM + RAG budget optimization
│   ├── content_agent.py       # Gemini bilingual ad copy generator
│   └── engagement_agent.py    # HuggingFace sentiment + Gemini reply generator
├── shared/
│   ├── mcp_schema.py          # Pydantic v2 MCPRequest / MCPResponse
│   └── security.py            # Fernet encryption, input sanitizer, rate limiter
├── ir/
│   └── vector_store.py        # ChromaDB setup, seeding, and query functions
├── mock_data/
│   ├── meta_ads_account.json  # Simulated Meta Ads account data
│   ├── campaign_metrics.json  # Campaign performance metrics
│   └── past_campaigns.json    # Historical campaigns for RAG
├── frontend/
│   └── dashboard.py           # Streamlit interactive UI
├── .env.example               # Environment variable template
├── requirements.txt           # Python dependencies
└── README.md
```

---

## 🔀 Git Branching Strategy

```
main  ─────────────────────────────────────────── (Final submission only)
  └─ development ──────────────────────────────── (All PRs merge here)
        ├─ feature/orchestrator-security
        ├─ feature/diagnostic-performance-agents
        ├─ feature/vector-store
        ├─ feature/budget-agent
        ├─ feature/content-engagement
        └─ feature/frontend-dashboard
```

**Rules:**
- Never push directly to `main` or `development`.
- Always open a Pull Request with at least 1 reviewer approval.
- Always sync `development` before starting work: `git pull origin development`.

---

## 🧪 Testing Agents Standalone

```bash
# Diagnostic Agent
python -c "from agents.diagnostic_agent import run; print(run({}))"

# Performance Agent
python -c "from agents.performance_agent import run; print(run({}))"

# Budget Agent
python -c "from agents.budget_agent import run; print(run({}))"

# Content Agent
python -c "from agents.content_agent import run; print(run({'product': 'Jeans', 'offer': '20% off', 'tone': 'friendly'}))"

# Engagement Agent
python -c "from agents.engagement_agent import run; print(run({'comment': 'Great product!', 'dry_run': True}))"

# Shared modules
python -c "from shared.mcp_schema import MCPRequest, MCPResponse; from shared.security import sanitize_input, encrypt_token, decrypt_token, RateLimiter; print('All shared modules OK')"
```

---

## 🔒 Security Notes

- All LLM inputs are sanitized by `shared.security.sanitize_input()` to block prompt-injection attacks.
- Sensitive tokens (e.g., API keys at runtime) can be encrypted with `encrypt_token()` / `decrypt_token()`.
- Never commit `.env`. It is in `.gitignore`.
- The `FERNET_KEY` must be consistent across all teammates for encryption to work correctly.
