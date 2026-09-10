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

    total_ad_sets = len(ad_sets)
    active_ad_sets = 0
    inactive_completed = 0
    disapproved_ads = 0
    total_daily_budget_active = 0.0

    for ad_set in ad_sets:
        daily_budget = float(ad_set.get("daily_budget", 0) or 0)
        status = ad_set.get("status", "ACTIVE")
        is_inactive = status in ("PAUSED", "COMPLETED")

        if is_inactive:
            inactive_completed += 1
            msg = "Campaign completed and reached its schedule end date." if status == "COMPLETED" else "Ad set is paused in Meta."
            issues.append({
                "type": "inactive_completed",
                "severity": "info",
                "ad_set_id": ad_set.get("id"),
                "ad_set_name": ad_set.get("name"),
                "campaign_id": ad_set.get("campaign_id"),
                "status": status,
                "daily_budget": daily_budget,
                "est_impr_loss": 0,
                "message": msg,
            })
        else:
            active_ad_sets += 1
            total_daily_budget_active += daily_budget

        for ad in ad_set.get("ads", []):
            if ad.get("review_status") == "DISAPPROVED":
                disapproved_ads += 1
                issues.append({
                    "type": "disapproved_ad",
                    "severity": "critical",
                    "ad_id": ad.get("id"),
                    "ad_name": ad.get("name"),
                    "ad_set_id": ad_set.get("id"),
                    "campaign_id": ad_set.get("campaign_id"),
                    "issues": ad.get("issues", ["Policy violation: Content flags"]),
                    "message": "Ad was disapproved by Meta platform policy review.",
                })
                recommendations.append({
                    "issue_type": "disapproved_ad",
                    "action": f"Fix compliance policy violation on ad '{ad.get('name')[:25]}'",
                    "target_id": ad.get("id"),
                })

    billing_status = account.get("billing_status", "OK")
    if billing_status != "OK":
        issues.append({
            "type": "billing_issue",
            "severity": "critical",
            "billing_status": billing_status,
            "message": "The account payment method requires verification or update.",
        })
        recommendations.append({
            "issue_type": "billing_issue",
            "action": "Update or verify the payment method in Meta Ads Manager.",
            "target_id": account.get("account_id"),
        })

    # --- Enterprise Pillar Health Breakdown Calculation ---
    # 1. Delivery Health: Inactive completed ads are normal business operations, not penalties
    delivery_score = 95 if (billing_status == "OK" and disapproved_ads == 0) else 60

    # 2. Policy & Compliance Health (Disapprovals)
    policy_score = 100 if disapproved_ads == 0 else max(0, 100 - (disapproved_ads * 35))

    # 3. Budget & Billing Health
    budget_score = 100 if billing_status == "OK" else 20

    # 4. Tracking & Signal Health (Base benchmark)
    tracking_score = 98

    # Overall Composite Weighted Health Score
    overall_health_score = int(
        (delivery_score * 0.35) +
        (policy_score * 0.30) +
        (budget_score * 0.20) +
        (tracking_score * 0.15)
    )

    # Filter critical/active issues count vs completed archives
    critical_issues = [i for i in issues if i.get("severity") in ("critical", "high", "warning")]

    return {
        "account_id": account.get("account_id"),
        "account_name": account.get("account_name"),
        "currency": account.get("currency", "USD"),
        "amount_spent": account.get("amount_spent"),
        "billing_status": billing_status,
        "health_score": overall_health_score,
        "health_pillars": {
            "delivery": {"score": delivery_score, "label": "Delivery & Live Reach", "status": "Operational"},
            "policy": {"score": policy_score, "label": "Meta Policy Compliance", "status": "Clean" if policy_score > 85 else "Action Required"},
            "budget": {"score": budget_score, "label": "Budget & Billing Health", "status": "Active" if billing_status == "OK" else "Payment Alert"},
            "tracking": {"score": tracking_score, "label": "Tracking & Signal Health", "status": "Connected"}
        },
        "summary": {
            "issue_count": len(critical_issues),
            "total_ad_sets": total_ad_sets,
            "paused_ad_sets": inactive_completed,
            "active_ad_sets": active_ad_sets,
            "disapproved_ads": disapproved_ads,
            "healthy": len(critical_issues) == 0,
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