"""
SENTINEL AI X — Business Impact Engine.

Quantifies the financial risk of security vulnerabilities by mapping
threats to business assets and estimating breach costs, regulatory
fines, operational downtime, and reputational damage.

Uses the Ponemon/IBM Cost of Data Breach methodology adapted
for software-specific risk factors.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

# ── Cost coefficients (USD, based on IBM 2024 report) ─────────────
BASE_BREACH_COST = 4_880_000  # avg cost of a data breach
COST_PER_RECORD = 165         # per-record cost

SEVERITY_MULTIPLIER = {
    "critical": 1.0, "high": 0.6, "medium": 0.3, "low": 0.1, "info": 0.0,
}

# ── Regulatory penalty estimates by framework ────────────────────
REGULATORY_PENALTIES: dict[str, dict[str, Any]] = {
    "GDPR":   {"max_fine_pct": 0.04, "base_fine": 20_000_000, "regions": ["EU", "EEA"]},
    "HIPAA":  {"max_fine_pct": 0.0,  "base_fine": 2_000_000,  "regions": ["US"]},
    "PCI_DSS": {"max_fine_pct": 0.0, "base_fine": 500_000,    "regions": ["global"]},
    "SOC2":   {"max_fine_pct": 0.0,  "base_fine": 250_000,    "regions": ["global"]},
    "SOX":    {"max_fine_pct": 0.0,  "base_fine": 5_000_000,  "regions": ["US"]},
    "CCPA":   {"max_fine_pct": 0.0,  "base_fine": 7_500,      "regions": ["US-CA"]},
}

# ── Asset criticality weights ────────────────────────────────────
ASSET_CRITICALITY = {
    "Secret": 0.95, "DatabaseConnection": 0.9, "AuthFlow": 0.85,
    "APIEndpoint": 0.7, "Infrastructure": 0.8, "CloudResource": 0.75,
    "Container": 0.6, "DockerImage": 0.55, "TerraformResource": 0.7,
    "ExternalService": 0.65, "DataFlow": 0.6, "TrustBoundary": 0.5,
    "GitHubAction": 0.4, "Module": 0.35, "File": 0.2,
    "Function": 0.15, "Class": 0.15, "Dependency": 0.3,
}

# ── Downtime cost per hour by industry (simplified) ──────────────
DOWNTIME_COST_PER_HOUR = {
    "fintech": 540_000, "healthcare": 636_000, "e-commerce": 220_000,
    "saas": 150_000, "enterprise": 300_000, "default": 200_000,
}


class BusinessImpactEngine:
    """
    Computes financial risk metrics for repository vulnerabilities.

    Combines threat severity, asset criticality, blast radius,
    compliance exposure, and downtime estimates to produce
    dollar-value risk scores.
    """

    def __init__(self, driver=None) -> None:
        self._driver = driver

    async def compute_repository_impact(
        self,
        repo_full_name: str,
        annual_revenue: float = 10_000_000,
        industry: str = "default",
        estimated_records: int = 100_000,
        compliance_frameworks: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Compute full business impact assessment for a repository.
        """
        frameworks = compliance_frameworks or ["GDPR", "SOC2"]

        # Gather threat data from Neo4j
        threats = await self._get_repo_threats(repo_full_name)
        assets = await self._get_repo_assets(repo_full_name)
        chains = await self._get_attack_chains(repo_full_name)

        # ── Per-threat impact ────────────────────────────────
        threat_impacts = []
        total_financial_risk = 0.0

        for threat in threats:
            sev = threat.get("severity", "medium")
            mult = SEVERITY_MULTIPLIER.get(sev, 0.3)

            # Base breach cost scaled by severity
            breach_cost = BASE_BREACH_COST * mult

            # Record exposure cost
            record_cost = COST_PER_RECORD * estimated_records * mult * 0.1

            # Asset criticality factor
            affected_assets = self._find_affected_assets(
                threat.get("id", ""), assets
            )
            asset_factor = max(
                (ASSET_CRITICALITY.get(a.get("type", ""), 0.2)
                 for a in affected_assets),
                default=0.2,
            )

            # Downtime estimate
            downtime_hours = {"critical": 72, "high": 24, "medium": 8, "low": 2}.get(sev, 4)
            hourly_rate = DOWNTIME_COST_PER_HOUR.get(industry, DOWNTIME_COST_PER_HOUR["default"])
            downtime_cost = downtime_hours * hourly_rate * mult

            # Total for this threat
            threat_total = (breach_cost + record_cost + downtime_cost) * asset_factor
            total_financial_risk += threat_total

            threat_impacts.append({
                "threat_id": threat.get("id", ""),
                "title": threat.get("title", "Unknown"),
                "severity": sev,
                "breach_cost": round(breach_cost, 2),
                "record_exposure_cost": round(record_cost, 2),
                "downtime_cost": round(downtime_cost, 2),
                "downtime_hours": downtime_hours,
                "asset_criticality": round(asset_factor, 3),
                "affected_asset_count": len(affected_assets),
                "total_impact": round(threat_total, 2),
            })

        # Sort by impact
        threat_impacts.sort(key=lambda t: t["total_impact"], reverse=True)

        # ── Regulatory exposure ──────────────────────────────
        regulatory_exposure = []
        total_regulatory_risk = 0.0
        for fw in frameworks:
            pen = REGULATORY_PENALTIES.get(fw)
            if not pen:
                continue
            base = pen["base_fine"]
            pct_fine = pen["max_fine_pct"] * annual_revenue if pen["max_fine_pct"] > 0 else 0
            fine = max(base, pct_fine)
            # Scale by number of relevant threats
            relevant = len([t for t in threats if t.get("category") in
                          ("compliance", "data_exposure", "authentication", "authorization", "secrets")])
            exposure = fine * min(1.0, relevant * 0.15)
            total_regulatory_risk += exposure
            regulatory_exposure.append({
                "framework": fw,
                "max_fine": round(fine, 2),
                "estimated_exposure": round(exposure, 2),
                "relevant_threat_count": relevant,
                "regions": pen["regions"],
            })

        # ── Chain amplification ──────────────────────────────
        chain_amplification = 1.0
        if chains:
            max_chain_score = max(c.get("severity_score", 0) for c in chains)
            chain_amplification = 1.0 + min(0.5, max_chain_score * 0.1)

        # ── Summary ──────────────────────────────────────────
        grand_total = (total_financial_risk + total_regulatory_risk) * chain_amplification

        return {
            "repo_full_name": repo_full_name,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_financial_risk": round(grand_total, 2),
                "breach_cost_total": round(sum(t["breach_cost"] for t in threat_impacts), 2),
                "downtime_cost_total": round(sum(t["downtime_cost"] for t in threat_impacts), 2),
                "record_exposure_total": round(sum(t["record_exposure_cost"] for t in threat_impacts), 2),
                "regulatory_exposure_total": round(total_regulatory_risk, 2),
                "chain_amplification_factor": round(chain_amplification, 3),
                "threat_count": len(threats),
                "critical_threats": len([t for t in threats if t.get("severity") == "critical"]),
                "high_value_assets": len([a for a in assets if ASSET_CRITICALITY.get(a.get("type", ""), 0) >= 0.7]),
                "attack_chain_count": len(chains),
            },
            "industry": industry,
            "annual_revenue": annual_revenue,
            "estimated_records": estimated_records,
            "compliance_frameworks": frameworks,
            "threat_impacts": threat_impacts[:30],
            "regulatory_exposure": regulatory_exposure,
            "risk_rating": self._risk_rating(grand_total),
        }

    # ─────────────────────────────────────────────────────────
    # Neo4j Queries
    # ─────────────────────────────────────────────────────────

    async def _get_repo_threats(self, repo: str) -> list[dict]:
        if not self._driver:
            return []
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Repository {full_name: $repo})-[:HAS_THREAT]->(t:Threat)
                RETURN t.id AS id, t.title AS title, t.severity AS severity,
                       t.category AS category, t.cwe_id AS cwe,
                       t.mitre_technique AS mitre
                ORDER BY t.severity DESC
                LIMIT 100
                """,
                repo=repo,
            )
            return [dict(r) async for r in result]

    async def _get_repo_assets(self, repo: str) -> list[dict]:
        if not self._driver:
            return []
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Repository {full_name: $repo})-[*1..2]-(a)
                WHERE NOT a:Repository AND NOT a:Threat AND NOT a:Vulnerability
                RETURN DISTINCT a.id AS id,
                       coalesce(a.name, a.title, a.label, a.path, toString(id(a))) AS label,
                       labels(a)[0] AS type,
                       coalesce(a.risk, 0.0) AS risk
                LIMIT 200
                """,
                repo=repo,
            )
            return [dict(r) async for r in result]

    async def _get_attack_chains(self, repo: str) -> list[dict]:
        if not self._driver:
            return []
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (ac:AttackChain {repo_full_name: $repo})
                RETURN ac.id AS id, ac.severity_score AS severity_score,
                       ac.chain_length AS chain_length
                ORDER BY ac.severity_score DESC
                LIMIT 20
                """,
                repo=repo,
            )
            return [dict(r) async for r in result]

    def _find_affected_assets(
        self, threat_id: str, assets: list[dict]
    ) -> list[dict]:
        """Simple heuristic — in production this would query the graph."""
        # Return assets with highest criticality as proxy
        return sorted(
            assets, key=lambda a: ASSET_CRITICALITY.get(a.get("type", ""), 0),
            reverse=True,
        )[:5]

    @staticmethod
    def _risk_rating(total: float) -> str:
        if total >= 5_000_000:
            return "CRITICAL"
        if total >= 1_000_000:
            return "HIGH"
        if total >= 250_000:
            return "MEDIUM"
        return "LOW"
