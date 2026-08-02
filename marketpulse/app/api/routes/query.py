"""app/api/routes/query.py — Natural language query endpoint (the showpiece)."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.api.auth import require_api_key
from app.agents.query_agent.agent import run_query, stream_query_events
from app.config import settings as _settings

router = APIRouter(prefix="/query", tags=["query"])

class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Natural language question about market data",
        examples=["What is the current RSI for AAPL?", "Is TSLA showing any anomalies today?"],
    )

class AgentStep(BaseModel):
    agent_name: str
    tool_name: str
    tool_input: str
    tool_output: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    steps: List[AgentStep] = Field(default_factory=list, description="Internal reasoning steps and tool execution trace.")


@router.post("", response_model=QueryResponse)
async def natural_language_query(
    body: QueryRequest,
    session_id: str = "default",
    _: str = Depends(require_api_key),
):
    """
    Ask a natural language question about your tracked stocks.

    The agent will:
    1. Decide which data to fetch based on your question
    2. Run statistical analysis if needed
    3. Return a synthesized answer

    Example questions:
    - "What happened to AAPL today?"
    - "Is TSLA RSI showing overbought conditions?"
    - "Which tickers had anomalies in the last 24 hours?"
    - "Give me a trend summary for MSFT"
    """
    if session_id == "default":
        import uuid
        session_id = str(uuid.uuid4())
        
    answer, steps = await run_query(body.question, session_id=session_id)
    return QueryResponse(question=body.question, answer=answer, steps=steps)



@router.get("/stream")
async def stream_natural_language_query(
    question: str,
    session_id: str = "default",
    api_key: str = "",
):
    """
    Stream the agent's progress and final answer via Server-Sent Events (SSE).
    Pass api_key as a query parameter: /query/stream?question=...&api_key=...
    """
    if api_key != _settings.api_key:
        import secrets
        if not secrets.compare_digest(api_key, _settings.api_key):
            return JSONResponse(status_code=403, content={"detail": "Invalid or missing API key."})
    
    if session_id == "default":
        import uuid
        session_id = str(uuid.uuid4())
        
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return StreamingResponse(stream_query_events(question, session_id=session_id), media_type="text/event-stream")

