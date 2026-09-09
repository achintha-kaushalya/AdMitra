"""Rule-based health diagnostics for a Meta Ads account."""

import json
from pathlib import Path
from typing import Any

from shared.mcp_schema import MCPResponse


AGENT_NAME = "DiagnosticAgent"
ACCOUNT_DATA_PATH = Path(__file__).resolve().parents[1] / "mock_data" / "meta_ads_account.json"


try:
    from shared.meta_api import fetch_live_ad_account
except ImportError:
    fetch_live_ad_account = None


def _load_account() -> dict[str, Any]:
    if fetch_live_ad_account:
        live_data = fetch_live_ad_account()
        if live_data:
            return live_data

    with ACCOUNT_DATA_PATH.open(encoding="utf-8") as account_file:
        data = json.load(account_file)
    if not isinstance(data, dict):
        raise ValueError("Meta Ads account data must be a JSON object")
    return data


def _diagnose(account: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    ad_sets = account.get("ad_sets", [])

    for ad_set in ad_sets:
        if ad_set.get("status") == "PAUSED":
            issues.append({
                "type": "paused_ad_set",
                "severity": "warning",
                "ad_set_id": ad_set.get("id"),
                "ad_set_name": ad_set.get("name"),
                "message": "Ad set is paused and cannot deliver ads.",
            })
            recommendations.append({
                "issue_type": "paused_ad_set",
                "action": "Review the ad set settings and resume it if the campaign should be active.",
                "target_id": ad_set.get("id"),
            })

        for ad in ad_set.get("ads", []):
            if ad.get("review_status") == "DISAPPROVED":
                issues.append({
                    "type": "disapproved_ad",
                    "severity": "critical",
                    "ad_id": ad.get("id"),
                    "ad_name": ad.get("name"),
                    "ad_set_id": ad_set.get("id"),
                    "issues": ad.get("issues", []),
                    "message": "Ad was disapproved during platform review.",
                })
                recommendations.append({
                    "issue_type": "disapproved_ad",
                    "action": "Correct the listed policy issues and submit the ad for review again.",
                    "target_id": ad.get("id"),
                })

    billing_status = account.get("billing_status")
    if billing_status != "OK":
        issues.append({
            "type": "billing_issue",
            "severity": "critical",
            "billing_status": billing_status,
            "message": "The account billing status requires attention.",
        })
        recommendations.append({
            "issue_type": "billing_issue",
            "action": "Update or verify the payment method before campaigns are interrupted.",
            "target_id": account.get("account_id"),
        })

    return {
        "account_id": account.get("account_id"),
        "account_name": account.get("account_name"),
        "billing_status": billing_status,
        "summary": {
            "issue_count": len(issues),
            "ad_set_count": len(ad_sets),
            "healthy": not issues,
        },
        "issues": issues,
        "recommended_actions": recommendations,
    }


def run(input: dict) -> dict:
    """Analyze the configured mock Meta Ads account."""
    del input
    try:
        return MCPResponse.success(AGENT_NAME, _diagnose(_load_account())).model_dump()
    except Exception as exc:
        return MCPResponse.error(AGENT_NAME, f"Diagnostic analysis failed: {exc}").model_dump()