# Project: MarketPulse Institutional Terminal

## Tech Stack
- **Backend**: Python 3.12, FastAPI, LangGraph, LangChain, SQLAlchemy (Async), PostgreSQL, Redis, Pydantic v2
- **Frontend**: Vanilla HTML5, Vanilla CSS3 (Glassmorphism design tokens), Vanilla JavaScript (ES6+), FontAwesome
- **Data Scraping**: Custom 7-Stage Scraping Pipeline (`web_scraper` multi-adapter engine)

## Common Commands
- **Run API Server**: `.\env\Scripts\python -m uvicorn app.api.main:app --reload` (from `marketpulse/`)
- **Run Unit Tests**: `.\env\Scripts\python -m pytest marketpulse`
- **Run Pipeline**: `.\env\Scripts\python marketpulse/run_pipeline.py`
- **Run Test Agent**: `.\env\Scripts\python marketpulse/test_agent.py`

## Code Conventions
- Prefer standard libraries and async I/O (`asyncio.to_thread` for blocking I/O calls).
- Keep statistical analysis and zero-cost checks separated from expensive LLM calls.
- Enforce strict typing with Pydantic models and SQLAlchemy AsyncSession.
- All frontend UI code uses Vanilla CSS and modern HTML tokens defined in `ui/DESIGN.md`.

## Security & Reliability Boundaries
- Never commit raw API keys or PostgreSQL passwords in code.
- Always parameterize database queries via SQLAlchemy ORM.
- Validate all incoming user queries before processing.
