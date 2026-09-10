"""
orchestrator/main.py — AdMitra FastAPI Orchestrator
====================================================
Central routing layer that receives MCP requests and delegates to
the appropriate specialist agent. Exposes three HTTP endpoints.

Endpoints:
  GET  /health        → Basic liveness check.
  POST /run-agent     → Routes a single MCPRequest to the correct agent.
  POST /check-account → Runs ALL 5 agents in parallel and returns aggregated results.

Author  : Member 1 — Backend Lead
Project : AdMitra (IT3041 — IRWA, SLIIT)
"""

import importlib
import sys
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is on the path so agent modules resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.mcp_schema import MCPRequest, MCPResponse


# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------
# Maps task name → (module_path, default_payload)
# Agents will be imported lazily when first requested.
AGENT_REGISTRY: dict[str, dict[str, Any]] = {
    "diagnostic": {
        "module": "agents.diagnostic_agent",
        "default_payload": {},
    },
    "performance": {
        "module": "agents.performance_agent",
        "default_payload": {},
    },
    "budget": {
        "module": "agents.budget_agent",
        "default_payload": {},
    },
    "content": {
        "module": "agents.content_agent",
        "default_payload": {
            "product": "Sample Product",
            "offer": "Special offer — limited time",
            "tone": "friendly",
        },
    },
    "engagement": {
        "module": "agents.engagement_agent",
        "default_payload": {
            "comment": "Great product, really happy with it!",
            "dry_run": True,
        },
    },
}


def _load_agent(task: str):
    """
    Dynamically import and return the agent module for the given task name.
    Returns a mock/fallback agent if the module is not yet implemented by a teammate.
    """
    if task not in AGENT_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown task '{task}'. Valid tasks: {list(AGENT_REGISTRY.keys())}",
        )
    module_path = AGENT_REGISTRY[task]["module"]
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError:
        # Teammate's agent module not yet merged — return a stub response
        return None


def _call_agent(task: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Calls the agent's run(payload) function.
    Falls back to a placeholder response if the agent module doesn't exist yet.
    """
    agent_module = _load_agent(task)
    if agent_module is None:
        # Graceful fallback for modules not yet implemented by teammates
        return MCPResponse(
            status="pending",
            agent=task.capitalize() + "Agent",
            result={
                "message": f"Agent module '{task}' is not yet deployed. "
                           "Teammate branch not merged yet."
            },
            timestamp=datetime.utcnow().isoformat(),
        ).model_dump()
    try:
        raw = agent_module.run(payload)
        return raw if isinstance(raw, dict) else MCPResponse.model_validate(raw).model_dump()
    except Exception as exc:
        return MCPResponse.error(
            agent=task.capitalize() + "Agent",
            message=str(exc),
        ).model_dump()


# ---------------------------------------------------------------------------
# App Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    print("[AdMitra] Orchestrator starting up...")
    yield
    print("[AdMitra] Orchestrator shutting down.")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AdMitra Orchestrator",
    description=(
        "Central MCP-style orchestrator for the AdMitra multi-agent "
        "digital marketing AI system."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Restrict to Streamlit origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """
    Liveness check endpoint.
    Returns HTTP 200 with {"status": "ok"} when the orchestrator is running.
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/run-agent", response_model=MCPResponse, tags=["Agents"])
def run_agent(request: MCPRequest) -> dict[str, Any]:
    """
    Route a single MCPRequest to the correct specialist agent.

    Body:
        task    : One of "diagnostic", "performance", "budget", "content", "engagement".
        payload : Agent-specific key-value payload.

    Returns:
        MCPResponse with agent result or error details.
    """
    return _call_agent(request.task, request.payload)


from concurrent.futures import ThreadPoolExecutor

@app.post("/check-account", tags=["Agents"])
def check_account(body: dict[str, Any] = {}) -> dict[str, Any]:
    """
    Run ALL 5 agents in parallel using ThreadPoolExecutor for lightning-fast response.
    Each agent receives the full body dict as its payload.

    Returns:
        Aggregated dict with results from every agent keyed by task name.
    """
    tasks = list(AGENT_REGISTRY.keys())

    def _execute(task_name: str) -> tuple[str, dict[str, Any]]:
        config = AGENT_REGISTRY[task_name]
        payload = {**config["default_payload"], **body}
        return task_name, _call_agent(task_name, payload)

    results: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_execute, t) for t in tasks]
        for f in futures:
            task_name, res = f.result()
            results[task_name] = res

    return {
        "status": "success",
        "agents_run": tasks,
        "results": results,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Dev Server Entry-Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("orchestrator.main:app", host="0.0.0.0", port=8000, reload=True)
