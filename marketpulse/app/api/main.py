"""
app/api/main.py — FastAPI application entry point.
Sets up lifespan (DB init), mounts all routes, and configures observability.
"""
import os
import logging
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import init_db
from app.api.routes import status, tickers, query

# Configure standard logging to redirect to structlog
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

# Setup structlog for JSON production logs and colored local logs
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True) if os.getenv("ENVIRONMENT") != "production" else structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before accepting requests."""
    logger.info("api_startup", action="starting MarketPulse API")
    from app.config import settings

    # Warn about missing LLM key but keep the app alive — stock price
    # fetching (yfinance) works fine without it; only NL agent queries fail.
    try:
        key = settings.llm_api_key
        logger.info("llm_key_loaded", provider="nvidia" if settings.nvidia_api_key else "openrouter")
    except ValueError:
        logger.warning("llm_key_missing", warning="No NVIDIA_API_KEY or OPENROUTER_API_KEY set. AI agent queries will be disabled.")

    # DB init is optional — if no DATABASE_URL is configured the app still
    # serves the UI and yfinance-based stock lookups.
    try:
        await init_db()
        logger.info("database_ready", action="DB tables created/verified")
    except Exception as db_err:
        logger.warning("database_unavailable", error=str(db_err), warning="Running without persistent DB. Portfolio storage disabled.")

    logger.info("api_live", action="API is live")
    yield
    logger.info("api_shutdown", action="MarketPulse API shutting down")


app = FastAPI(
    title="MarketPulse API",
    description=(
        "Real-time market data pipeline with statistical anomaly detection "
        "and a natural language query agent powered by LangGraph."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Observability Middlewares
app.add_middleware(CorrelationIdMiddleware)

@app.middleware("http")
async def structlog_middleware(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    req_id = correlation_id.get()
    if req_id:
        structlog.contextvars.bind_contextvars(request_id=req_id)
    structlog.contextvars.bind_contextvars(
        method=request.method,
        path=request.url.path,
    )
    return await call_next(request)

# Mount Prometheus Metrics
Instrumentator().instrument(app).expose(app)

# Mount routers
app.include_router(status.router)
app.include_router(tickers.router)
app.include_router(query.router)

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Mount static assets (background image, etc.) from canonical ui/ folder
_ui_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../ui"))
_assets_dir = os.path.join(_ui_dir, "assets")
if not os.path.isdir(_assets_dir):
    _assets_dir = os.path.join(os.path.dirname(__file__), "templates", "assets")

if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

@app.get("/", tags=["root"], response_class=HTMLResponse)
async def root():
    """Serves the MarketPulse Institutional Terminal frontend."""
    template_path = os.path.join(_ui_dir, "index.html")
    if not os.path.isfile(template_path):
        template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Frontend UI not found.</h1><p>Check the ui/ folder.</p>"

