# ==============================================================================
# MarketPulse AI: Production Multi-Stage Dockerfile
# Serves FastAPI Asynchronous Gateway + Static Institutional Terminal UI
# ==============================================================================
FROM python:3.12-slim as runtime

# Set environment variables for clean Python execution & module resolution
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/marketpulse:/app/web_scraper \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# Install system dependencies required for database connectors and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and institutional UI
COPY marketpulse/ /app/marketpulse/
COPY web_scraper/ /app/web_scraper/
COPY ui/ /app/ui/

# Expose API port
EXPOSE 8000

# Health check to ensure API readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/status || exit 1

# Launch FastAPI Server
WORKDIR /app/marketpulse
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
