"""LLM function-calling router.

Exposes:
* ``GET /llm/tools``   — returns tool definitions
* ``POST /llm/query``  — accepts a natural-language question, uses Google Gemini
                          function calling to resolve it against the data
                          connectors, and returns a voice-friendly answer.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.connectors.analytics_connector import AnalyticsConnector
from app.services.business_rules import apply_business_rules
from app.services.data_identifier import identify_data_type
from app.services.voice_optimizer import build_voice_summary, freshness_label
from app.models.common import DataResponse, Metadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Function Calling"])


# ────────────────────────────────────────────────────────────────────
# Tool definitions (OpenAI-compatible)
# ────────────────────────────────────────────────────────────────────

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_crm",
            "description": (
                "Search and retrieve customer CRM records.  Use this when the "
                "user asks about customers, accounts, users, or contacts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive"],
                        "description": "Filter customers by account status.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Partial name search (case-insensitive).",
                    },
                    "email": {
                        "type": "string",
                        "description": "Partial email search.",
                    },
                    "customer_id": {
                        "type": "integer",
                        "description": "Exact customer ID lookup.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max records to return (default 10).",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["customer_id", "name", "created_at", "status"],
                        "description": "Field to sort by.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_support_tickets",
            "description": (
                "Search and retrieve support tickets.  Use this when the user "
                "asks about tickets, issues, bugs, complaints, or support requests."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["open", "closed"],
                        "description": "Filter tickets by status.",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Filter tickets by priority level.",
                    },
                    "customer_id": {
                        "type": "integer",
                        "description": "Filter tickets belonging to a specific customer.",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Search ticket subjects (partial match).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max records to return (default 10).",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["ticket_id", "priority", "created_at", "status"],
                        "description": "Field to sort by.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_analytics",
            "description": (
                "Retrieve analytics and metrics data.  Use this when the user "
                "asks about metrics, DAU, daily active users, usage stats, or trends."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "Metric name to filter (e.g. daily_active_users).",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date inclusive (YYYY-MM-DD).",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date inclusive (YYYY-MM-DD).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max records to return (default 10).",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["date", "value", "metric"],
                        "description": "Field to sort by.",
                    },
                },
                "required": [],
            },
        },
    },
]


@router.get("/tools", summary="Get LLM tool definitions")
def get_tools():
    """Return OpenAI-compatible function / tool definitions.

    An LLM (or orchestration layer) calls this once to discover what
    functions are available and their parameter schemas.
    """
    return {
        "tools": TOOL_DEFINITIONS,
        "instruction": (
            "You are a helpful voice assistant for a SaaS company. "
            "Use the above tools to answer user questions about customers, "
            "support tickets, and analytics.  Always prefer short, "
            "spoken-friendly answers."
        ),
    }


# ────────────────────────────────────────────────────────────────────
# Natural-language query endpoint (uses OpenAI function calling)
# ────────────────────────────────────────────────────────────────────

class LLMQueryRequest(BaseModel):
    """Request body for the /llm/query endpoint."""
    question: str = Field(
        ...,
        description="Natural-language question from the user",
        examples=["How many open support tickets are there?"],
    )
    voice_mode: bool = Field(True, description="Optimise response for voice")


class LLMQueryResponse(BaseModel):
    """Response from the /llm/query endpoint."""
    question: str
    answer: str
    function_called: Optional[str] = None
    function_args: Optional[Dict[str, Any]] = None
    data: Optional[DataResponse] = None


@router.post(
    "/query",
    response_model=LLMQueryResponse,
    summary="Ask a question (LLM function calling)",
    description=(
        "Send a natural-language question.  The server will use Google Gemini's "
        "function calling to decide which data connector to query and return "
        "a voice-optimised answer."
    ),
)
async def llm_query(body: LLMQueryRequest):
    """End-to-end:  question → LLM decides tool → connector → answer."""

    if not settings.GOOGLE_API_KEY:
        # Fallback to rule-based routing when no API key
        return _rule_based_query(body.question, body.voice_mode)

    try:
        return await _gemini_function_call(body.question, body.voice_mode)
    except Exception as exc:
        logger.error("Gemini call failed: %s — falling back to rule-based", exc)
        return _rule_based_query(body.question, body.voice_mode)


# ────────────────────────────────────────────────────────────────────
# Google Gemini-powered path
# ────────────────────────────────────────────────────────────────────

async def _gemini_function_call(question: str, voice_mode: bool) -> LLMQueryResponse:
    """Use Google Gemini (via langchain-google-genai) with function calling."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatGoogleGenerativeAI(
        model=settings.GOOGLE_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
    )

    # Convert tool definitions to langchain-compatible tools
    tools = _build_langchain_tools()
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=(
            "You are a helpful voice assistant for a SaaS company. "
            "Answer questions about customers, support tickets, and "
            "analytics by calling the provided functions. "
            "Keep answers concise and suitable for voice output."
        )),
        HumanMessage(content=question),
    ]

    # Step 1: ask the model which function to call
    response = llm_with_tools.invoke(messages)

    # No function call — model answered directly
    if not response.tool_calls:
        return LLMQueryResponse(
            question=question,
            answer=response.content or "I'm not sure how to answer that.",
        )

    tool_call = response.tool_calls[0]
    fn_name = tool_call["name"]
    fn_args = tool_call["args"]

    logger.info("LLM chose function=%s args=%s", fn_name, fn_args)

    # Step 2: execute the function locally
    data_response = _execute_function(fn_name, fn_args, voice_mode)

    # Step 3: feed result back to the model for a natural-language answer
    from langchain_core.messages import ToolMessage

    messages.append(response)
    messages.append(ToolMessage(
        content=json.dumps(data_response.model_dump(), default=str),
        tool_call_id=tool_call["id"],
    ))

    final = llm_with_tools.invoke(messages)
    answer = final.content or ""

    return LLMQueryResponse(
        question=question,
        answer=answer,
        function_called=fn_name,
        function_args=fn_args,
        data=data_response,
    )


def _build_langchain_tools():
    """Convert OpenAI-style TOOL_DEFINITIONS to langchain tool schemas."""
    from langchain_core.tools import tool as langchain_tool

    tools = []
    for td in TOOL_DEFINITIONS:
        fn = td["function"]
        fn_name = fn["name"]
        fn_desc = fn["description"]
        fn_params = fn["parameters"]

        # Build a JSON-schema-based tool for langchain
        tools.append({
            "type": "function",
            "function": {
                "name": fn_name,
                "description": fn_desc,
                "parameters": fn_params,
            },
        })
    return tools


# ────────────────────────────────────────────────────────────────────
# Rule-based fallback (works without API key)
# ────────────────────────────────────────────────────────────────────

# Order matters — more specific keywords first to avoid false matches
_KEYWORD_MAP = [
    ("analytics", ["metric", "metrics", "analytics", "dau", "daily active", "usage", "trend", "stats"]),
    ("support", ["ticket", "tickets", "issue", "issues", "bug", "complaint", "support"]),
    ("crm", ["customer", "customers", "account", "accounts", "user", "users", "contact", "crm"]),
]


def _rule_based_query(question: str, voice_mode: bool) -> LLMQueryResponse:
    """Simple keyword-based routing when no LLM API key is available."""
    q_lower = question.lower()
    source = None
    for src, keywords in _KEYWORD_MAP:
        if any(kw in q_lower for kw in keywords):
            source = src
            break

    if not source:
        return LLMQueryResponse(
            question=question,
            answer="I can help with customer data, support tickets, and analytics. Could you please rephrase your question?",
        )

    # Extract simple filters from question
    filters = _extract_filters_from_question(q_lower, source)
    fn_name = {"crm": "query_crm", "support": "query_support_tickets", "analytics": "query_analytics"}[source]

    data_response = _execute_function(fn_name, filters, voice_mode)

    answer = data_response.metadata.voice_summary or f"Found {data_response.metadata.total_results} results."

    return LLMQueryResponse(
        question=question,
        answer=answer,
        function_called=fn_name,
        function_args=filters,
        data=data_response,
    )


def _extract_filters_from_question(question: str, source: str) -> Dict[str, Any]:
    """Basic keyword extraction for rule-based mode."""
    filters: Dict[str, Any] = {}

    if source == "support":
        if "open" in question:
            filters["status"] = "open"
        elif "closed" in question:
            filters["status"] = "closed"
        if "high" in question and "priority" in question:
            filters["priority"] = "high"
        elif "medium" in question:
            filters["priority"] = "medium"
        elif "low" in question:
            filters["priority"] = "low"
    elif source == "crm":
        if "active" in question and "inactive" not in question:
            filters["status"] = "active"
        elif "inactive" in question:
            filters["status"] = "inactive"
    # analytics — no keyword filters needed for a simple query

    return filters


# ────────────────────────────────────────────────────────────────────
# Shared function executor
# ────────────────────────────────────────────────────────────────────

_FUNCTION_CONNECTOR = {
    "query_crm": ("crm", CRMConnector),
    "query_support_tickets": ("support", SupportConnector),
    "query_analytics": ("analytics", AnalyticsConnector),
}


def _execute_function(
    fn_name: str,
    fn_args: Dict[str, Any],
    voice_mode: bool = True,
) -> DataResponse:
    """Run a function-calling request against the correct connector."""
    if fn_name not in _FUNCTION_CONNECTOR:
        raise HTTPException(status_code=400, detail=f"Unknown function: {fn_name}")

    source, ConnectorCls = _FUNCTION_CONNECTOR[fn_name]
    connector = ConnectorCls()

    limit = fn_args.pop("limit", 10)
    sort_by = fn_args.pop("sort_by", None)
    sort_order = fn_args.pop("sort_order", "desc")
    offset = fn_args.pop("offset", 0)
    filters = {k: v for k, v in fn_args.items() if v is not None}

    result = connector.fetch(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=1000,
        offset=0,
    )

    items = result["items"]
    total = result["total"]

    ruled = apply_business_rules(source, items, limit=limit)
    data_type = identify_data_type(ruled)

    voice_summary = None
    if voice_mode:
        voice_summary = build_voice_summary(source, ruled, total, filters)

    metadata = Metadata(
        total_results=total,
        returned_results=len(ruled),
        page=1,
        page_size=limit,
        has_more=len(items) > limit,
        data_type=data_type,
        data_freshness=freshness_label(),
        voice_summary=voice_summary,
        filters_applied=filters,
    )

    return DataResponse(source=source, data=ruled, metadata=metadata)
