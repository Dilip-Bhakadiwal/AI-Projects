"""
app/agents/nodes/analyst_node.py — LLM synthesis node.
Called ONLY when stats_engine detects an anomaly (confidence > threshold).
Uses NVIDIA NIM (free) or OpenRouter Gemma (free) via OpenAI-compatible API.
"""
import json
import logging

import httpx

from app.analysis.stats_engine import AnalysisResult
from app.config import settings

logger = logging.getLogger(__name__)

ANOMALY_PROMPT = """You are a financial analyst. Given the following statistical anomaly detected in stock data, explain in 2-3 sentences what this likely means for investors. Be specific and factual. Do not make buy/sell recommendations.

Ticker: {ticker}
Statistical Finding: {description}
Last Close Price: ${last_close:.2f}
Z-Score: {zscore}
RSI: {rsi}
Price Change (last bar): {price_change_pct}

Respond with ONLY a JSON object in this exact format:
{{"summary": "your 2-3 sentence explanation", "severity": "low|medium|high"}}"""



async def call_llm(prompt: str) -> dict:
    """
    Call NVIDIA NIM or OpenRouter with a prompt.
    Returns parsed JSON dict from LLM response.
    """
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    # OpenRouter requires this header
    if "openrouter" in settings.llm_base_url:
        headers["HTTP-Referer"] = "https://github.com/marketpulse"

    payload = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 256,
        "temperature": 0.3,  # low temp for factual financial analysis
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        if resp.status_code != 200:
            logger.error(
                "LLM API returned %d: %s",
                resp.status_code,
                resp.text[:500],
            )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"].strip()
    tokens_used = data.get("usage", {}).get("total_tokens", 0)

    # Strip markdown code fences if LLM wraps in ```json
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    parsed = json.loads(content.strip())
    parsed["_tokens"] = tokens_used
    return parsed


async def run_analyst_node(stats_result: AnalysisResult) -> dict:
    """
    Main entry point for LangGraph analyst node.
    Returns dict with 'summary', 'severity', '_tokens', '_model'.
    """
    prompt = ANOMALY_PROMPT.format(
        ticker=stats_result.ticker,
        description=stats_result.description,
        last_close=stats_result.last_close,
        zscore=f"{stats_result.zscore:.2f}" if stats_result.zscore is not None else "N/A",
        rsi=f"{stats_result.rsi:.1f}" if stats_result.rsi is not None else "N/A",
        price_change_pct=f"{stats_result.price_change_pct:+.2%}" if stats_result.price_change_pct is not None else "N/A",
    )

    try:
        result = await call_llm(prompt)
        result["_model"] = settings.llm_model
        logger.info(
            "LLM synthesis for %s: tokens=%d severity=%s",
            stats_result.ticker, result.get("_tokens", 0), result.get("severity", "?")
        )
        return result
    except json.JSONDecodeError as e:
        logger.error("LLM returned non-JSON for %s: %s", stats_result.ticker, e)
        return {
            "summary": stats_result.description,  # fallback to stats description
            "severity": "low",
            "_tokens": 0,
            "_model": "fallback",
        }
    except Exception as e:
        logger.error("LLM call failed for %s: %s", stats_result.ticker, e, exc_info=True)
        return {
            "summary": stats_result.description,
            "severity": "low",
            "_tokens": 0,
            "_model": "error",
        }
