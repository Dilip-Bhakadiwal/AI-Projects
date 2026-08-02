# MarketPulse 📈

MarketPulse is a professional-grade, agentic AI platform for real-time market data ingestion and analysis. It is designed to be highly resilient, cost-effective, and fully autonomous.

## Architecture

This project implements an enterprise-level streaming pipeline:
1. **Ingestion Layer:** Asynchronously fetches ticker data (e.g., from Yahoo Finance) and pushes it to a Redis Stream buffer.
2. **Processing Layer:** A consumer pulls from Redis and bulk-inserts into a PostgreSQL database, ensuring database write-locks never slow down data fetching.
3. **Analysis Layer (LangGraph):** Uses a state machine (LangGraph) to route data. It first runs a lightweight statistical engine (Z-score, RSI) to detect anomalies. Only if an anomaly is detected does it trigger an expensive LLM (NVIDIA NIM or OpenRouter) to synthesize a summary, saving up to 95% on API costs.
4. **Query Agent:** A ReAct agent that allows you to ask natural language questions about your market data. It uses tools to query the PostgreSQL database directly.

## Tech Stack
- **Backend:** FastAPI (Python 3.12)
- **Database:** PostgreSQL (asyncpg, SQLAlchemy)
- **Queue/Buffer:** Redis Streams
- **Agents:** LangGraph, LangChain
- **LLM Integrations:** NVIDIA NIM (Llama 3.1), OpenRouter (Gemma)

## Getting Started

### 1. Prerequisites
- Python 3.12
- PostgreSQL 18
- Redis

### 2. Installation
```bash
# Set up virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies (ensure these are in your requirements.txt)
pip install fastapi uvicorn sqlalchemy asyncpg redis langgraph langchain langchain-openai pydantic yfinance pandas pytest httpx
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in your credentials.
- `DATABASE_URL`: Your PostgreSQL connection string.
- `REDIS_URL`: Your Redis connection string.
- `LLM_BASE_URL` & `LLM_API_KEY`: NVIDIA NIM or OpenRouter.

### 4. Running the Project

**Start the API Server:**
```bash
cd marketpulse
..\venv\Scripts\uvicorn.exe app.api.main:app --host 127.0.0.1 --port 8000 --reload
```
You can now access the interactive API docs at `http://127.0.0.1:8000/docs`.

**Start the Background Worker (Scheduler):**
In a new terminal window:
```bash
cd marketpulse
..\venv\Scripts\python.exe app/worker.py
```

### 5. Running Tests
The project includes a full unit test suite (15 tests) for validation and the statistics engine.
```bash
cd marketpulse
..\venv\Scripts\python.exe -m pytest tests/ -v
```

## Usage

1. **Add a Ticker:** `POST /tickers` with body `{"ticker": "AAPL", "name": "Apple Inc."}`
2. **Check Health:** `GET /status`
3. **View Signals:** `GET /signals/AAPL`
4. **Query Agent:** `POST /query` with body `{"question": "What is the recent analysis for AAPL?"}`
