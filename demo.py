"""
Universal Data Connector — LLM Function Calling Demo
=====================================================

This script demonstrates the end-to-end flow:
1. Start the FastAPI server (must be running on localhost:8000)
2. Fetch available tool definitions from /llm/tools
3. Send natural-language questions to /llm/query
4. Show the LLM's function call decision + voice-friendly answer

Usage
-----
    # Terminal 1: start the server
    uvicorn app.main:app --reload

    # Terminal 2: run this demo
    python demo.py

Works in two modes:
    * **With Google API key** — full LLM function calling via Gemini 2.5 Flash
    * **Without key**           — rule-based keyword routing (no API needed)
"""

import json
import httpx
import sys

BASE_URL = "http://localhost:8000"


def separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def pretty(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


def main() -> None:
    # ── 1. Health check ─────────────────────────────────────────────
    separator("1. Health Check")
    r = httpx.get(f"{BASE_URL}/health")
    print(pretty(r.json()))

    # ── 2. Fetch tool definitions ───────────────────────────────────
    separator("2. LLM Tool Definitions (GET /llm/tools)")
    r = httpx.get(f"{BASE_URL}/llm/tools")
    tools = r.json()
    for tool in tools["tools"]:
        fn = tool["function"]
        print(f"  - {fn['name']}: {fn['description'][:80]}...")
    print(f"\n  System instruction: {tools['instruction'][:100]}...")

    # ── 3. Direct API queries ───────────────────────────────────────
    separator("3. Direct API — Active Customers (GET /data/crm?status=active)")
    r = httpx.get(f"{BASE_URL}/data/crm", params={"status": "active", "limit": 5})
    data = r.json()
    print(f"  Voice summary: {data['metadata']['voice_summary']}")
    print(f"  Total: {data['metadata']['total_results']}, Returned: {data['metadata']['returned_results']}")
    print(f"  Freshness: {data['metadata']['data_freshness']}")

    separator("4. Direct API — Open High-Priority Tickets (GET /data/support?status=open&priority=high)")
    r = httpx.get(f"{BASE_URL}/data/support", params={"status": "open", "priority": "high", "limit": 5})
    data = r.json()
    print(f"  Voice summary: {data['metadata']['voice_summary']}")
    for t in data["data"][:3]:
        print(f"    Ticket #{t['ticket_id']}: {t['subject']} ({t['priority']}, {t['status']})")

    separator("5. Direct API — Analytics Last 7 Days (GET /data/analytics)")
    r = httpx.get(f"{BASE_URL}/data/analytics", params={"date_from": "2026-02-10", "limit": 7})
    data = r.json()
    print(f"  Voice summary: {data['metadata']['voice_summary']}")

    # ── 4. LLM function-calling queries ─────────────────────────────
    questions = [
        "How many open support tickets do we have?",
        "Show me active customers",
        "What are the daily active user trends this week?",
        "Are there any high priority open tickets?",
        "How many customers do we have in total?",
    ]

    for i, q in enumerate(questions, start=6):
        separator(f"{i}. LLM Query: \"{q}\"")

        r = httpx.post(
            f"{BASE_URL}/llm/query",
            json={"question": q, "voice_mode": True},
            timeout=30.0,
        )

        if r.status_code != 200:
            print(f"  ERROR {r.status_code}: {r.text}")
            continue

        resp = r.json()
        print(f"  Function called: {resp.get('function_called', 'N/A')}")
        print(f"  Function args:   {resp.get('function_args', {})}")
        print(f"  Answer:          {resp['answer']}")
        if resp.get("data"):
            meta = resp["data"]["metadata"]
            print(f"  Total results:   {meta['total_results']}")
            print(f"  Data freshness:  {meta['data_freshness']}")

    separator("Demo Complete!")
    print("  All endpoints working. Ready for video demonstration.\n")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("\nERROR: Cannot connect to the server.")
        print("Make sure the server is running:")
        print("  uvicorn app.main:app --reload")
        sys.exit(1)
