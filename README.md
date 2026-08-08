<div align="center">

# 🔮 OBSIDIAN

### Autonomous AI Security Engineering Organization

*An autonomous multi-agent AI platform for the Secure Software Development Lifecycle*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-FF6F00?logo=langchain&logoColor=white)](https://langchain.com)
[![NVIDIA](https://img.shields.io/badge/NVIDIA_NIM-Build_API-76B900?logo=nvidia&logoColor=white)](https://build.nvidia.com)
<br>
[![Deployed on Vercel](https://img.shields.io/badge/Deployed_on-Vercel-000000?logo=vercel&logoColor=white)](https://obsidian-rwnd.vercel.app)
[![Deployed on Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?logo=render&logoColor=white)](https://render.com)

[Live Demo](https://obsidian-rwnd.vercel.app) · [API Docs](https://obsidian-backend-gute.onrender.com/docs) · [Deployment Guide](DEPLOYMENT.md)

</div>

---

## 🎯 What is OBSIDIAN?

**OBSIDIAN** is not a chatbot, not a code review tool, and not a GitHub Copilot clone.

It is an **entire autonomous Security Engineering Organization** where **19 specialized AI agents** collaborate to analyze, secure, repair, test, document, and approve software before deployment — all triggered by a single `git push`.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         OBSIDIAN PIPELINE                                │
│                                                                          │
│  git push → Webhook → Event Sourcing → Digital Twin Update →             │
│  Knowledge Graph → 13 Parallel Scan Agents (incl. Threat Evolution) →    │
│  Attack Chain Discovery → Attack Simulation → Auto-Patch → Test Gen →   │
│  Business Impact Analysis → Deployment Approval (GO/NO-GO) → Learn      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Frontend — Next.js 15"
        UI[Dashboard — 13 Pages]
        AUTH[NextAuth GitHub OAuth]
    end

    subgraph "API Layer — FastAPI"
        API[REST API Gateway]
        WH[GitHub Webhooks]
        WS[WebSocket Manager]
        ONBOARD[Onboarding API]
    end

    subgraph "Processing"
        CEL[Celery Workers]
        LG[LangGraph Orchestrator]
    end

    subgraph "AI Agents — 19 Total"
        subgraph "Scan Phase — Parallel"
            TM[Threat Modeler]
            CI[Code Intelligence]
            AR[Architecture Review]
            DI[Dependency Intel]
            SD[Secrets Detection]
            IS[Infra Security]
            CS[Container Security]
            CL[Cloud Security]
            AS_[API Security]
            BL[Business Logic]
            LS[LLM Security]
            CO[Compliance]
            TE[Threat Evolution]
        end
        subgraph "Action Phase — Sequential"
            ATK[Attack Simulation]
            AP[Auto Patcher]
            RT[Regression Tester]
            DOC[Documentation]
            DA[Deployment Approval]
            LA[Learning Agent]
        end
    end

    subgraph "Advanced Engines"
        DT[Digital Twin Service]
        ACE[Attack Chain Engine]
        BIE[Business Impact Engine]
        TEE[Threat Evolution Engine]
    end

    subgraph "Knowledge Layer"
        NEO[Neo4j Graph DB]
        QD[Qdrant Vector DB]
        KB[Security KB: OWASP, MITRE, CWE]
    end

    subgraph "Infrastructure"
        PG[PostgreSQL]
        RD[Redis]
        NV[NVIDIA NIM API]
    end

    UI --> API
    AUTH --> API
    WH --> API
    API --> CEL
    CEL --> LG
    LG --> TM & CI & AR & DI & SD & IS & CS & CL & AS_ & BL & LS & CO & TE
    LG --> ATK --> AP --> RT --> DOC --> DA --> LA
    TM & CI & AR --> NEO & QD
    ATK --> ACE --> NEO
    TE --> TEE --> NEO
    AP --> NV
    LG --> DT --> NEO
    LG --> BIE
    LG --> PG
    CEL --> RD
    WS --> UI
```

---

## 🤖 The 19 Agents

| # | Agent | Tier | Phase | Purpose |
|---|-------|------|-------|---------|
| 1 | **Threat Modeler** | Reasoning | Scan | STRIDE/DREAD analysis, attack trees, MITRE ATT&CK mapping |
| 2 | **Architecture Reviewer** | Reasoning | Scan | Trust boundaries, design flaws, security anti-patterns |
| 3 | **Code Intelligence** | Code | Scan | Deep SAST — injection, XSS, auth bypass, data flow |
| 4 | **Dependency Intel** | Lightweight | Scan | CVE scanning, license compliance, supply chain risk |
| 5 | **Secrets Detection** | Lightweight | Scan | API keys, credentials, tokens, private keys |
| 6 | **Infra Security** | Code | Scan | Terraform, Ansible, K8s misconfigurations |
| 7 | **Container Security** | Code | Scan | Dockerfile analysis, image hardening |
| 8 | **Cloud Security** | Code | Scan | AWS/GCP/Azure misconfiguration detection |
| 9 | **API Security** | Code | Scan | OWASP API Top 10, rate limiting, auth gaps |
| 10 | **Business Logic** | Reasoning | Scan | Race conditions, auth bypass, logic flaws |
| 11 | **LLM Security** | Reasoning | Scan | Prompt injection, RAG poisoning, agent jailbreak |
| 12 | **Compliance** | Lightweight | Scan | GDPR, SOC2, HIPAA, PCI-DSS gap analysis |
| 13 | **Threat Evolution** | Reasoning | Scan | Predict threat mutation, weaponisation probability, kill-chain progression |
| 14 | **Attack Simulation** | Reasoning | Action | Chain vulnerabilities into attack paths |
| 15 | **Auto Patcher** | Code | Action | Generate production-quality security patches |
| 16 | **Regression Tester** | Code | Action | Generate tests that verify patches |
| 17 | **Documentation** | Code | Action | Update SECURITY.md, CHANGELOG |
| 18 | **Deployment Approval** | Reasoning | Action | GO/NO-GO decision with confidence scoring |
| 19 | **Learning Agent** | Reasoning | Action | Learn patterns to improve future runs |

---

## 🧠 Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM Backend** | NVIDIA NIM (Build API) | Multi-tier model routing (reasoning/code/lightweight) |
| **Agent Orchestration** | LangGraph | State machine pipeline with conditional event routing |
| **Knowledge Graph** | Neo4j | Attack path discovery, digital twin, threat evolution |
| **RAG Pipeline** | Qdrant | Semantic search over OWASP, MITRE, CWE knowledge bases |
| **API** | FastAPI | Async REST API with webhook + WebSocket support |
| **Task Queue** | Celery + Redis | Async event processing and pipeline execution |
| **Database** | PostgreSQL | Scan results, findings, patches, event sourcing |
| **Frontend** | Next.js 15 + React 19 | 13-page cybersecurity dashboard with Cytoscape.js |
| **Authentication** | NextAuth.js | GitHub OAuth login with JWT session management |
| **Graph Viz** | Cytoscape.js | Interactive Digital Twin graph rendering |
| **Real-time** | WebSocket | Live graph mutation broadcasts |

---

## 🔮 Advanced Engines

| Engine | Purpose |
|--------|---------|
| **AI Security Digital Twin** | Live Neo4j mirror of repository state updated on every GitHub event (22 event types). Visualised with Cytoscape.js in real-time via WebSocket. |
| **Threat Evolution Engine** | Tracks how threats mutate over time with temporal snapshots. Predicts 30/60/90-day weaponisation probability via NVIDIA NIM. |
| **Attack Chain Movie** | Discovers multi-step attack paths via graph traversal and replays them cinematically with MITRE kill-chain progression. |
| **Business Impact Engine** | Dollar-value risk quantification using IBM breach cost methodology, regulatory fines (GDPR/HIPAA/PCI-DSS/SOC2/SOX/CCPA), and downtime-by-industry estimates. |
| **Security Timeline Engine** | Historical point-in-time snapshots of full repository security posture allowing structural diffing, replay, and posture trend analysis. |

---

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (for full-stack)
- **Node.js 18+** and **Python 3.12+** (for local development)
- **GitHub Personal Access Token** (with `read:user`, `user:email`, `repo` scopes)
- **NVIDIA NIM API Key** — [Get one free at build.nvidia.com](https://build.nvidia.com)

### 1. Clone & Configure

```bash
git clone https://github.com/MDWASIULLAH/obsidian.git
cd obsidian
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start All Services (Docker)

```bash
docker compose up -d
```

### 3. Local Development (Without Docker)

```bash
# Backend
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

### 4. Access

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **API Health** | http://localhost:8000/health |
| **Neo4j Browser** | http://localhost:7474 |
| **Qdrant UI** | http://localhost:6333/dashboard |

### 5. Register a Repository

```bash
curl -X POST http://localhost:8000/api/v1/repositories \
  -H "Content-Type: application/json" \
  -d '{"full_name": "owner/repo-name"}'
```

### 6. Trigger a Manual Scan

```bash
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Content-Type: application/json" \
  -d '{"repository_id": "<repo-id>"}'
```

---

## 🌍 Production Deployment

OBSIDIAN is deployed on free-tier cloud infrastructure:

| Component | Provider | URL |
|-----------|----------|-----|
| **Frontend** | Vercel | [obsidian-rwnd.vercel.app](https://obsidian-rwnd.vercel.app) |
| **Backend** | Render | [obsidian-backend-gute.onrender.com](https://obsidian-backend-gute.onrender.com) |

For full deployment instructions, see the [Deployment Guide](DEPLOYMENT.md).

---

## 📁 Project Structure

```
obsidian/
├── backend/
│   ├── app/
│   │   ├── agents/                  # All 19 AI agents + orchestrator
│   │   │   ├── base.py              # BaseAgent abstract class
│   │   │   ├── state.py             # LangGraph pipeline state (event-aware)
│   │   │   ├── orchestrator.py      # LangGraph state machine + event routing
│   │   │   ├── registry.py          # Agent factory & registry
│   │   │   ├── threat_modeler.py
│   │   │   ├── code_intelligence.py
│   │   │   ├── threat_evolution_agent.py  # Threat trajectory prediction
│   │   │   ├── security_agents.py   # 10 scan agents
│   │   │   └── action_agents.py     # 6 action agents
│   │   ├── api/
│   │   │   ├── router.py            # REST API (30+ endpoints)
│   │   │   ├── auth.py              # Backend auth sync endpoint
│   │   │   ├── onboarding.py        # GitHub App onboarding flow
│   │   │   └── websocket.py         # Digital Twin WebSocket manager
│   │   ├── config.py                # Settings (all env vars, model config)
│   │   ├── core/
│   │   │   ├── model_router.py      # NVIDIA NIM multi-tier routing
│   │   │   └── prompts.py           # 19 agent system prompts
│   │   ├── integrations/
│   │   │   └── github_client.py     # GitHub API + GraphQL + 22-event parser
│   │   ├── knowledge/
│   │   │   ├── graph.py             # Neo4j knowledge graph (20+ node types)
│   │   │   ├── digital_twin.py      # AI Security Digital Twin service
│   │   │   ├── threat_evolution.py  # Temporal threat tracking engine
│   │   │   ├── attack_chain.py      # Attack path discovery + movie gen
│   │   │   ├── business_impact.py   # Dollar-value risk quantification
│   │   │   ├── rag.py               # Qdrant RAG pipeline
│   │   │   └── security_kb.py       # OWASP/MITRE/CWE data
│   │   ├── models/
│   │   │   ├── github_event.py      # Event sourcing model
│   │   │   ├── agent_run.py         # Agent execution run model
│   │   │   ├── database.py          # Engine, session, base model
│   │   │   ├── schemas.py           # 40+ Pydantic schemas
│   │   │   └── ...                  # SQLAlchemy models
│   │   ├── tasks/
│   │   │   └── celery_app.py        # Async event + pipeline tasks
│   │   ├── utils/                   # Utility functions
│   │   └── main.py                  # FastAPI application factory
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── auth/[...nextauth]/  # NextAuth GitHub OAuth handler
│   │   │   │   └── github/repos/        # GitHub repos API route
│   │   │   ├── dashboard/               # 13 dashboard pages
│   │   │   │   ├── page.tsx              # Overview with security gauge
│   │   │   │   ├── layout.tsx            # Sidebar navigation layout
│   │   │   │   ├── setup/               # GitHub App install onboarding
│   │   │   │   ├── repositories/        # User repo list from GitHub
│   │   │   │   ├── scans/               # Scan history
│   │   │   │   ├── threats/             # Finding explorer
│   │   │   │   ├── agents/              # Agent grid (19 agents)
│   │   │   │   ├── graph/               # Knowledge graph viz
│   │   │   │   ├── digital-twin/        # Cytoscape.js graph + WebSocket
│   │   │   │   ├── threat-evolution/    # Temporal timeline + predictions
│   │   │   │   ├── security-timeline/   # Snapshot history + diffing
│   │   │   │   ├── attack-chain/        # Cinematic attack replay
│   │   │   │   ├── business-impact/     # Dollar-value risk dashboard
│   │   │   │   ├── reports/             # Security reports
│   │   │   │   └── settings/            # User settings
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── layout.tsx            # Root layout
│   │   │   └── globals.css           # Global styles + design tokens
│   │   └── lib/
│   │       ├── api.ts                # Typed API client (30+ methods)
│   │       └── utils.ts              # Utility functions
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml                # Full-stack Docker orchestration
├── Makefile                          # Developer commands
├── render.yaml                       # Render deployment blueprint
├── DEPLOYMENT.md                     # Production deployment guide
├── .env.example                      # Environment variable template
└── README.md                         # ← You are here
```

---

## 🌐 API Endpoints Reference

All endpoints are prefixed with `/api/v1`.

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check with service status |
| `GET` | `/dashboard/overview` | Aggregate stats (repos, scans, findings, agents) |

### Authentication & Onboarding

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/sync` | Sync NextAuth user to backend (auto-called on login) |
| `POST` | `/onboarding/github-app/install-url` | Get GitHub App installation URL |
| `POST` | `/onboarding/github-app/sync-installation` | Sync GitHub App installation |

### Repositories

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/repositories` | Register a GitHub repository for monitoring |
| `GET` | `/repositories` | List all registered repositories |
| `GET` | `/repositories/{id}` | Get repository details |
| `DELETE` | `/repositories/{id}` | Remove a repository |

### Scans & Findings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scans` | Trigger a manual security scan |
| `GET` | `/scans` | List scan history (paginated) |
| `GET` | `/scans/{id}` | Get scan details with agent runs |
| `GET` | `/scans/{id}/findings` | List findings for a scan |
| `GET` | `/findings/{id}` | Get finding details with patches |
| `GET` | `/agents` | List all available agents and their status |

### GitHub Events & Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/webhooks/github` | Receive GitHub webhook events (HMAC-verified) |
| `GET` | `/events/{repo_id}` | List GitHub events for a repo (paginated, filterable) |

### Digital Twin

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/digital-twin/{repo}` | Get full twin graph (nodes + edges) |
| `GET` | `/digital-twin/{repo}/search` | Search twin nodes by label/type |
| `GET` | `/digital-twin/{repo}/node/{id}` | Get detailed node info |
| `WS` | `/ws/digital-twin/{repo_id}` | WebSocket for live graph mutation updates |

### Threat Evolution

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/threat-evolution/{repo}/timelines` | List all threat evolution timelines |
| `GET` | `/threat-evolution/{repo}/timeline/{id}` | Get full timeline with snapshots |
| `GET` | `/threat-evolution/prediction/{id}` | Get LLM-predicted trajectory |
| `GET` | `/threat-evolution/{repo}/exploitability` | Exploitability rankings (top N) |

### Attack Chains

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/attack-chains/{repo}/discover` | Discover chains via graph traversal |
| `GET` | `/attack-chains/{repo}/list` | List persisted attack chains |
| `POST` | `/attack-chains/movie` | Generate cinematic attack movie from chain |
| `GET` | `/attack-chains/{repo}/blast-radius/{node}` | Compute blast radius from a node |

### Business Impact

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/business-impact/{repo}` | Compute dollar-value risk assessment |

---

## 📺 Dashboard Pages (13)

| Page | Route | Description |
|------|-------|-------------|
| **Overview** | `/dashboard` | Security gauge, finding trends, recent scans |
| **Setup** | `/dashboard/setup` | GitHub App installation onboarding |
| **Repositories** | `/dashboard/repositories` | Browse repos from your GitHub account |
| **Scans** | `/dashboard/scans` | Scan history with status, duration, finding counts |
| **Threats** | `/dashboard/threats` | Finding explorer with severity filters and patches |
| **Agents** | `/dashboard/agents` | Agent grid showing 19 agents with tier/phase/status |
| **Knowledge Graph** | `/dashboard/graph` | Interactive graph of security relationships |
| **Digital Twin** | `/dashboard/digital-twin` | Live Cytoscape.js graph with WebSocket updates |
| **Threat Evolution** | `/dashboard/threat-evolution` | Timeline of threat mutations with LLM predictions |
| **Security Timeline** | `/dashboard/security-timeline` | Snapshot history, structural diffing, and 30-day trend |
| **Attack Chain** | `/dashboard/attack-chain` | Cinematic attack path replay with kill-chain viz |
| **Business Impact** | `/dashboard/business-impact` | Dollar-value risk gauge with regulatory exposure |
| **Reports** | `/dashboard/reports` | Exportable security assessment reports |
| **Settings** | `/dashboard/settings` | User preferences and configuration |

---

## 🔗 Supported GitHub Events (22)

The event sourcing layer captures and processes the following webhook event types:

| Category | Events |
|----------|--------|
| **Code Changes** | `push`, `pull_request`, `pull_request_review`, `pull_request_review_comment` |
| **Issues & Discussions** | `issues`, `issue_comment` |
| **Security Alerts** | `security_advisory`, `dependabot_alert`, `secret_scanning_alert`, `code_scanning_alert` |
| **Repository Management** | `create`, `delete`, `fork`, `star`, `repository` |
| **Releases & Deployments** | `release`, `deployment`, `deployment_status` |
| **Collaboration** | `member`, `team_add`, `organization` |
| **CI/CD** | `workflow_run`, `check_suite` |

---

## 🗃️ Neo4j Node Types (20+)

The knowledge graph schema includes the following node types with uniqueness constraints and indexes:

| Node Type | Purpose |
|-----------|---------|
| `Repository` | Root node — linked to all artefacts |
| `File`, `Module`, `Class`, `Function` | Code structure graph |
| `Vulnerability`, `Threat` | Security findings |
| `Dependency` | Third-party packages and CVEs |
| `APIEndpoint`, `AuthFlow`, `TrustBoundary` | Architecture graph |
| `Secret`, `DatabaseConnection` | High-value assets |
| `Infrastructure`, `CloudResource`, `Container`, `DockerImage` | Deployment graph |
| `ExternalService`, `DataFlow` | Data movement and integrations |
| `TerraformResource`, `GitHubAction` | IaC and CI/CD nodes |
| `ThreatSnapshot`, `PredictedTrajectory` | Temporal threat evolution |
| `AttackChain` | Persisted multi-step attack paths |

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NVIDIA_API_KEY` | ✅ | NVIDIA NIM Build API key |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `NEO4J_URI` | ✅ | Neo4j Bolt URI (e.g. `bolt://localhost:7687`) |
| `NEO4J_USER` | ✅ | Neo4j username |
| `NEO4J_PASSWORD` | ✅ | Neo4j password |
| `QDRANT_URL` | ✅ | Qdrant REST endpoint |
| `GITHUB_TOKEN` | ✅ | GitHub Personal Access Token or App token |
| `GITHUB_WEBHOOK_SECRET` | ✅ | HMAC secret for webhook verification |
| `GITHUB_ID` | ✅ | GitHub OAuth App Client ID |
| `GITHUB_SECRET` | ✅ | GitHub OAuth App Client Secret |
| `NEXTAUTH_URL` | ✅ | NextAuth callback URL (frontend URL) |
| `NEXTAUTH_SECRET` | ✅ | NextAuth encryption secret |
| `GITHUB_APP_ID` | ⬜ | GitHub App ID (for App auth mode) |
| `GITHUB_PRIVATE_KEY` | ⬜ | GitHub App RSA private key (PEM) |
| `GITHUB_INSTALLATION_ID` | ⬜ | GitHub App Installation ID |
| `NEXT_PUBLIC_API_URL` | ⬜ | Frontend API base URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | ⬜ | WebSocket base URL (default: auto-detected) |
| `GEMINI_API_KEY` | ⬜ | Google Gemini API key (optional fallback) |
| `GROQ_API_KEY` | ⬜ | Groq API key (optional fallback) |
| `OPENROUTER_API_KEY` | ⬜ | OpenRouter API key (optional fallback) |

---

## 🔐 Security Features

- **HMAC-SHA256 webhook verification** — Every GitHub event is cryptographically verified
- **GitHub App JWT authentication** — Secure installation-level access with RSA key signing
- **GitHub OAuth login** — Secure user authentication via NextAuth.js with GitHub provider
- **Event sourcing** — All 22 GitHub event types persisted with `payload_hash` for idempotency and time-travel
- **AI Security Digital Twin** — Live Neo4j graph mirror updated incrementally on every event via WebSocket
- **Threat Evolution tracking** — Temporal snapshots with velocity/trend metrics and 30/60/90-day weaponisation prediction
- **Attack Chain Movies** — Graph-traversal-based multi-step attack path discovery with cinematic replay
- **Business Impact quantification** — Dollar-value risk using IBM breach cost methodology + regulatory fines
- **Model tiering** — Sensitive code analyzed with reasoning-tier models, routine with lightweight
- **RAG citations** — Every finding includes source citations from OWASP/MITRE/CWE
- **Confidence scoring** — Every finding has a machine-learning confidence score
- **Auto-patching** — Production-ready patches with minimal, focused changes
- **Regression tests** — Automated test generation to verify patches
- **GO/NO-GO** — AI deployment approval with blocking for critical issues
- **Exploitability rankings** — Threats ranked by `severity × velocity × recency` for prioritised remediation

---

## 🛠️ Developer Commands (Makefile)

```bash
make setup          # Initial project setup (venv, npm install)
make up             # Start all Docker services
make down           # Stop all services
make backend        # Run backend in dev mode (uvicorn --reload)
make frontend       # Run frontend in dev mode (npm run dev)
make celery         # Run Celery worker
make test           # Run all tests
make lint           # Run linters (ruff, mypy, eslint)
make format         # Format code (ruff, prettier)
make kb-load        # Load security knowledge base into Qdrant
make kg-init        # Initialize Neo4j knowledge graph schema
make clean          # Clean build artifacts
```

---

## 📄 License

MIT License — Built for the AI Agent Hackathon.

---

<div align="center">

**Built with 🔮 using NVIDIA NIM • LangGraph • FastAPI • Neo4j • Qdrant • Next.js**

[GitHub](https://github.com/MDWASIULLAH/obsidian) · [Live Demo](https://obsidian-rwnd.vercel.app) · [API](https://obsidian-backend-gute.onrender.com/docs)

</div>
