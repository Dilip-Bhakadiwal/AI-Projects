"""
app/services/sql_guard.py — Production Security Guardrail for SQL Queries.

Provides strict read-only validation and sanitization for LLM-generated SQL statements.
Enforces:
  1. SELECT-only statement allowlist (no DDL/DML like DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE).
  2. Prevention of stacked/multiple queries (no embedded semicolons).
  3. Automatic LIMIT enforcement to prevent database denial-of-service or context-window overflow.
"""
import re
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)


class SecurityGuardrailException(Exception):
    """Raised when an LLM-generated action violates security or compliance guardrails."""
    pass


# Forbidden DDL, DML, and administrative SQL keywords (matched as full words)
_FORBIDDEN_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "CALL",
    "DO",
    "EXPLAIN",
    "ANALYZE",
    "VACUUM",
}


def validate_and_sanitize_sql(query: str, default_limit: int = 50, max_limit: int = 100) -> str:
    """
    Validate and sanitize an LLM-generated SQL query string.
    
    Returns the cleaned, safe SQL string ready for execution.
    Raises SecurityGuardrailException if the query attempts DDL/DML or violates safety rules.
    """
    if not query or not isinstance(query, str):
        raise SecurityGuardrailException("SQL Guardrail violation: Empty or invalid query input.")

    # 1. Strip leading/trailing whitespace and trailing semicolons
    cleaned = query.strip()
    while cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()

    # 2. Check for embedded semicolons (stacked query injection defense)
    if ";" in cleaned:
        logger.error("sql_guardrail_violation_stacked_query", query=query)
        raise SecurityGuardrailException(
            "SQL Guardrail violation: Stacked queries (multiple statements separated by ';') are forbidden."
        )

    # 3. Strip SQL comments (-- ... and /* ... */) before keyword inspection
    no_comments = re.sub(r"--.*?$|/\*.*?\*/", "", cleaned, flags=re.MULTILINE | re.DOTALL).strip()

    # 4. Enforce read-only SELECT allowlist
    upper_query = no_comments.upper()
    if not upper_query.startswith("SELECT") and not upper_query.startswith("WITH"):
        logger.error("sql_guardrail_violation_non_select", query=query)
        raise SecurityGuardrailException(
            "SQL Guardrail violation: Only read-only SELECT or WITH (CTE) queries are permitted."
        )

    # 5. Check for forbidden DDL/DML keyword tokens
    words = set(re.findall(r"\b[A-Z_]+\b", upper_query))
    violation_words = words.intersection(_FORBIDDEN_KEYWORDS)
    if violation_words:
        logger.error("sql_guardrail_violation_forbidden_keyword", keywords=list(violation_words), query=query)
        raise SecurityGuardrailException(
            f"SQL Guardrail violation: Forbidden keyword(s) detected: {', '.join(sorted(violation_words))}."
        )

    # 6. Enforce LIMIT constraint to prevent unbounded row fetching
    limit_match = re.search(r"\bLIMIT\s+(\d+)", upper_query)
    if not limit_match:
        cleaned = f"{cleaned} LIMIT {default_limit}"
        logger.info("sql_guardrail_injected_limit", default_limit=default_limit)
    else:
        current_limit = int(limit_match.group(1))
        if current_limit > max_limit:
            # Clamp the limit to max_limit
            cleaned = re.sub(
                r"\bLIMIT\s+\d+",
                f"LIMIT {max_limit}",
                cleaned,
                flags=re.IGNORECASE,
            )
            logger.info("sql_guardrail_clamped_limit", original=current_limit, clamped=max_limit)

    logger.info("sql_guardrail_passed", safe_query=cleaned)
    return cleaned
