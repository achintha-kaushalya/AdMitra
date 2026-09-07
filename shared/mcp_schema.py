"""
shared/mcp_schema.py — AdMitra MCP Communication Schema
========================================================
Defines the standard request/response Pydantic v2 models used across
all agent communication. Every agent MUST use these contracts.

Author  : Member 1 — Backend Lead
Project : AdMitra (IT3041 — IRWA, SLIIT)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MCPRequest(BaseModel):
    """
    Standard input contract for the AdMitra MCP system.

    Attributes:
        task    : Identifier for the target agent task.
                  One of: "diagnostic", "performance", "budget", "content", "engagement".
        payload : Arbitrary key-value data forwarded to the agent's run() function.
    """

    task: str = Field(
        ...,
        description="Target agent task name.",
        examples=["diagnostic", "performance", "budget", "content", "engagement"],
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific input payload.",
    )


class MCPResponse(BaseModel):
    """
    Standard output contract returned by every AdMitra agent.

    Attributes:
        status    : "success" or "error".
        result    : Agent output — structure varies per agent but is always a dict.
        agent     : Name of the agent that produced this response.
        timestamp : ISO-8601 UTC datetime string of when the response was created.
    """

    status: str = Field(..., examples=["success", "error"])
    result: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-produced output payload.",
    )
    agent: str = Field(..., description="Name of the producing agent.")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="UTC timestamp of response creation (ISO-8601).",
    )

    @classmethod
    def success(cls, agent: str, result: dict[str, Any]) -> "MCPResponse":
        """Convenience factory for successful responses."""
        return cls(status="success", agent=agent, result=result)

    @classmethod
    def error(cls, agent: str, message: str) -> "MCPResponse":
        """Convenience factory for error responses."""
        return cls(
            status="error",
            agent=agent,
            result={"message": message},
        )
