# Universal Data Connector

A production-ready **FastAPI** backend that provides a unified interface for an LLM-powered voice assistant to query multiple business data sources (CRM, Support Tickets, Analytics) using **Google Gemini function calling**.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash-4285F4?logo=google&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)

---

## Overview

Users ask natural-language questions through a voice assistant. The system uses **Gemini 2.5 Flash** to decide which data source to query, executes the query locally, and returns a concise, voice-friendly answer.

```
User: "How many open support tickets do we have?"
  ↓
POST /llm/query
  ↓
Gemini picks → query_support_tickets(status="open")
  ↓
Business Rules → Voice Optimizer
  ↓
"You have 5 open support tickets, 2 are high priority."
```

---

## Features

- **3 Data Connectors** — CRM customers, support tickets, analytics metrics
- **LLM Function Calling** — Gemini automatically selects the right data source
- **Voice-Optimized Responses** — concise summaries with context ("showing 3 of 47 results")
- **Business Rules Engine** — smart prioritization, result limiting, and sorting
- **Data Type Detection** — identifies tabular, time-series, or hierarchical data
- **Freshness Indicators** — "Data as of 2 minutes ago"
- **Rule-Based Fallback** — works without an API key via keyword routing
- **Docker Ready** — single command deployment

---

## Tech Stack

| Component | Technology |
|---|---|
| Framework | FastAPI + Pydantic v2 |
| LLM | Google Gemini 2.5 Flash (via `langchain-google-genai`) |
| Language | Python 3.11+ |
| Data | JSON mock data (simulates real databases) |
| Deployment | Docker + Docker Compose |

---

## Project Structure

```
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Environment-based configuration
│   ├── connectors/
│   │   ├── base.py                # Abstract base connector
│   │   ├── crm_connector.py       # Customer CRM data
│   │   ├── support_connector.py   # Support tickets
│   │   └── analytics_connector.py # Analytics & metrics
│   ├── models/                    # Pydantic v2 schemas
│   ├── routers/
│   │   ├── health.py              # GET /health
│   │   ├── data.py                # GET /data/{source}
│   │   └── llm.py                 # GET /llm/tools, POST /llm/query
│   ├── services/
│   │   ├── business_rules.py      # Filtering & prioritization
│   │   ├── data_identifier.py     # Data type detection
│   │   └── voice_optimizer.py     # Voice-friendly summaries
│   └── utils/
│       └── logging.py             # Logging configuration
├── data/                          # Mock JSON data files
├── tests/                         # Unit tests
├── demo.py                        # End-to-end demo script
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Google API Key ([get one free](https://aistudio.google.com/apikey))

### Installation

```bash
# Clone the repository
git clone https://github.com/P-Saroha/Universal-Data-Connector.git
cd Universal-Data-Connector

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_MODEL=gemini-2.5-flash
```

### Run the Server

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** to explore the interactive API docs.

### Run the Demo

In a separate terminal:

```bash
python demo.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/data/{source}` | Direct data query — `source`: `crm`, `support`, `analytics` |
| `GET` | `/llm/tools` | Returns function definitions for LLM tool calling |
| `POST` | `/llm/query` | Natural-language question → Gemini function calling → voice answer |

### Example: LLM Query

```bash
curl -X POST http://localhost:8000/llm/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many open support tickets do we have?", "voice_mode": true}'
```

**Response:**
```json
{
  "question": "How many open support tickets do we have?",
  "answer": "You currently have 5 open support tickets. 2 are high priority.",
  "function_called": "query_support_tickets",
  "function_args": {"status": "open"},
  "data": { "..." }
}
```

### Example: Direct Data Query

```bash
curl "http://localhost:8000/data/crm?status=active&limit=5"
```

---

## Docker

```bash
docker-compose up --build
```

Visit: **http://localhost:8000/docs**

---

## Running Tests

```bash
pytest tests/ -v
```

---

## How It Works

```
┌─────────────────────────────────────────────────┐
│                  POST /llm/query                │
│            "Show me active customers"           │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│           Google Gemini 2.5 Flash               │
│     Decides: query_crm(status="active")         │
└─────────────────┬───────────────────────────────┘
                  ↓
┌──────────┬──────────────┬───────────────────────┐
│   CRM    │   Support    │     Analytics         │
│Connector │  Connector   │     Connector         │
└──────────┴──────────────┴───────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│  Business Rules → Voice Optimizer → Response    │
└─────────────────────────────────────────────────┘
```

1. **User sends a question** via `POST /llm/query`
2. **Gemini decides** which function/connector to call and with what arguments
3. **Connector fetches** data from JSON files (simulating a real DB)
4. **Business rules** prioritize, limit, and sort the results
5. **Voice optimizer** generates a concise spoken-friendly summary
6. **Gemini formats** the final natural-language answer

Without an API key, the system falls back to **keyword-based routing** (no LLM needed).

---

## License

This project is for educational and demonstration purposes.
