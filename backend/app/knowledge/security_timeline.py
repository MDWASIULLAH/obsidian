"""
OBSIDIAN — Security Timeline Engine.

Creates point-in-time snapshots of repository security posture
and enables historical comparison, replay, and drift detection.

Core concepts
─────────────
  SecuritySnapshot   Full capture of security state at a moment in time.
  TimelineDiff       Delta between two snapshots showing what changed.
  ArchitectureDrift  Detected structural changes in the repository.
  PostureTimeline    Ordered sequence of snapshots with trend analysis.
"""

from __future__ import annotations

import hashlib
import json as _json
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog

logger = structlog.get_logger()

# ── Snapshot severity weights ─────────────────────────────────────
SEV_WEIGHT = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25, "info": 0.0}


class SecurityTimelineEngine:
    """
    Records and queries temporal security snapshots in Neo4j.

    Each snapshot captures the full security posture of a repository
    at a specific point in time, enabling historical comparison
    and drift detection.
    """

    def __init__(self, driver) -> None:
        self._driver = driver

    # ─────────────────────────────────────────────────────────
    # Schema
    # ─────────────────────────────────────────────────────────

    async def create_schema(self) -> None:
        stmts = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ss:SecuritySnapshot) REQUIRE ss.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (ss:SecuritySnapshot) ON (ss.repo_full_name)",
            "CREATE INDEX IF NOT EXISTS FOR (ss:SecuritySnapshot) ON (ss.captured_at)",
            "CREATE INDEX IF NOT EXISTS FOR (ad:ArchitectureDrift) REQUIRE ad.id IS UNIQUE",
        ]
        async with self._driver.session() as session:
            for s in stmts:
                try:
                    await session.run(s)
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────
    # Snapshot Capture
    # ─────────────────────────────────────────────────────────

    async def capture_snapshot(
        self,
        repo_full_name: str,
        trigger: str = "manual",
        event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Capture a full security snapshot of the repository's current state.

        Queries Neo4j for all threats, vulnerabilities, assets, and
        architecture nodes, then persists a SecuritySnapshot node.
        """
        now = datetime.now(timezone.utc)
        snapshot_id = hashlib.sha256(
            f"{repo_full_name}:{now.isoformat()}:{trigger}".encode()
        ).hexdigest()[:20]

        # Gather current state
        threats = await self._count_by_severity(repo_full_name, "Threat")
        vulns = await self._count_by_severity(repo_full_name, "Vulnerability")
        assets = await self._count_assets(repo_full_name)
        chains = await self._count_attack_chains(repo_full_name)
        score = await self._get_security_score(repo_full_name)

        snapshot = {
            "id": snapshot_id,
            "repo_full_name": repo_full_name,
            "captured_at": now.isoformat(),
            "trigger": trigger,
            "event_id": event_id,
            "security_score": score,
            "threat_counts": threats,
            "vulnerability_counts": vulns,
            "total_threats": sum(threats.values()),
            "total_vulnerabilities": sum(vulns.values()),
            "total_assets": assets.get("total", 0),
            "asset_breakdown": assets,
            "attack_chain_count": chains,
            "critical_findings": threats.get("critical", 0) + vulns.get("critical", 0),
            "high_findings": threats.get("high", 0) + vulns.get("high", 0),
            "risk_score": self._compute_risk_score(threats, vulns, chains),
        }

        # Persist to Neo4j
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (ss:SecuritySnapshot {id: $sid})
                SET ss.repo_full_name = $repo,
                    ss.captured_at = datetime($ts),
                    ss.trigger = $trigger,
                    ss.event_id = $eid,
                    ss.security_score = $score,
                    ss.total_threats = $tt,
                    ss.total_vulnerabilities = $tv,
                    ss.total_assets = $ta,
                    ss.attack_chain_count = $ac,
                    ss.critical_findings = $cf,
                    ss.high_findings = $hf,
                    ss.risk_score = $rs,
                    ss.data_json = $djson
                WITH ss
                MATCH (r:Repository {full_name: $repo})
                MERGE (r)-[:HAS_SNAPSHOT]->(ss)
                """,
                sid=snapshot_id, repo=repo_full_name, ts=now.isoformat(),
                trigger=trigger, eid=event_id, score=score,
                tt=snapshot["total_threats"], tv=snapshot["total_vulnerabilities"],
                ta=snapshot["total_assets"], ac=chains,
                cf=snapshot["critical_findings"], hf=snapshot["high_findings"],
                rs=snapshot["risk_score"],
                djson=_json.dumps(snapshot),
            )

        logger.info("Security snapshot captured",
                     snapshot_id=snapshot_id, repo=repo_full_name,
                     threats=snapshot["total_threats"])
        return snapshot

    # ─────────────────────────────────────────────────────────
    # Timeline Queries
    # ─────────────────────────────────────────────────────────

    async def get_timeline(
        self,
        repo_full_name: str,
        limit: int = 50,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get ordered list of security snapshots for a repository."""
        params: dict[str, Any] = {"repo": repo_full_name, "limit": limit}
        where = "ss.repo_full_name = $repo"
        if since:
            where += " AND ss.captured_at >= datetime($since)"
            params["since"] = since

        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MATCH (ss:SecuritySnapshot)
                WHERE {where}
                RETURN ss.id AS id,
                       ss.captured_at AS captured_at,
                       ss.trigger AS trigger,
                       ss.security_score AS security_score,
                       ss.total_threats AS total_threats,
                       ss.total_vulnerabilities AS total_vulnerabilities,
                       ss.total_assets AS total_assets,
                       ss.attack_chain_count AS attack_chain_count,
                       ss.critical_findings AS critical_findings,
                       ss.high_findings AS high_findings,
                       ss.risk_score AS risk_score
                ORDER BY ss.captured_at DESC
                LIMIT $limit
                """,
                **params,
            )
            snapshots = []
            async for rec in result:
                d = dict(rec)
                if d.get("captured_at"):
                    d["captured_at"] = str(d["captured_at"])
                snapshots.append(d)
            return snapshots

    async def get_snapshot_detail(
        self, snapshot_id: str
    ) -> dict[str, Any] | None:
        """Get full snapshot detail including breakdown data."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (ss:SecuritySnapshot {id: $sid})
                RETURN ss.data_json AS data_json,
                       ss.id AS id,
                       ss.captured_at AS captured_at
                """,
                sid=snapshot_id,
            )
            rec = await result.single()
            if not rec:
                return None
            data_json = rec.get("data_json")
            if data_json:
                try:
                    return _json.loads(data_json)
                except Exception:
                    pass
            return {"id": rec["id"], "captured_at": str(rec.get("captured_at"))}

    async def diff_snapshots(
        self,
        snapshot_a_id: str,
        snapshot_b_id: str,
    ) -> dict[str, Any]:
        """
        Compare two snapshots and return the delta.

        Returns changes in threat counts, vulnerability counts,
        security score, risk score, and asset counts.
        """
        a = await self.get_snapshot_detail(snapshot_a_id)
        b = await self.get_snapshot_detail(snapshot_b_id)

        if not a or not b:
            return {"error": "One or both snapshots not found"}

        def _delta(key: str) -> dict[str, Any]:
            va = a.get(key, 0) if not isinstance(a.get(key), dict) else 0
            vb = b.get(key, 0) if not isinstance(b.get(key), dict) else 0
            return {"before": va, "after": vb, "delta": vb - va}

        # Severity-level diffs for threats
        threat_a = a.get("threat_counts", {})
        threat_b = b.get("threat_counts", {})
        threat_diff = {}
        for sev in ("critical", "high", "medium", "low"):
            threat_diff[sev] = {
                "before": threat_a.get(sev, 0),
                "after": threat_b.get(sev, 0),
                "delta": threat_b.get(sev, 0) - threat_a.get(sev, 0),
            }

        return {
            "snapshot_a": {"id": snapshot_a_id, "captured_at": a.get("captured_at")},
            "snapshot_b": {"id": snapshot_b_id, "captured_at": b.get("captured_at")},
            "security_score": _delta("security_score"),
            "risk_score": _delta("risk_score"),
            "total_threats": _delta("total_threats"),
            "total_vulnerabilities": _delta("total_vulnerabilities"),
            "total_assets": _delta("total_assets"),
            "attack_chain_count": _delta("attack_chain_count"),
            "critical_findings": _delta("critical_findings"),
            "threat_severity_diff": threat_diff,
            "posture_direction": (
                "improving" if (b.get("risk_score", 0) or 0) < (a.get("risk_score", 0) or 0)
                else "degrading" if (b.get("risk_score", 0) or 0) > (a.get("risk_score", 0) or 0)
                else "stable"
            ),
        }

    async def get_posture_trend(
        self,
        repo_full_name: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Compute security posture trend over a time period.

        Returns aggregated metrics showing improvement or degradation.
        """
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        snapshots = await self.get_timeline(repo_full_name, limit=100, since=since)

        if len(snapshots) < 2:
            return {
                "repo_full_name": repo_full_name,
                "period_days": days,
                "snapshots_count": len(snapshots),
                "trend": "insufficient_data",
                "data_points": snapshots,
            }

        # Compute trend from first to last
        first = snapshots[-1]  # oldest
        last = snapshots[0]    # newest

        score_delta = (last.get("security_score") or 50) - (first.get("security_score") or 50)
        risk_delta = (last.get("risk_score") or 0) - (first.get("risk_score") or 0)
        threat_delta = (last.get("total_threats") or 0) - (first.get("total_threats") or 0)

        if score_delta > 5:
            trend = "improving"
        elif score_delta < -5:
            trend = "degrading"
        else:
            trend = "stable"

        return {
            "repo_full_name": repo_full_name,
            "period_days": days,
            "snapshots_count": len(snapshots),
            "trend": trend,
            "score_delta": score_delta,
            "risk_delta": round(risk_delta, 3),
            "threat_delta": threat_delta,
            "first_snapshot": first,
            "last_snapshot": last,
            "data_points": [
                {
                    "captured_at": s.get("captured_at"),
                    "security_score": s.get("security_score"),
                    "risk_score": s.get("risk_score"),
                    "total_threats": s.get("total_threats"),
                    "critical_findings": s.get("critical_findings"),
                }
                for s in reversed(snapshots)
            ],
        }

    # ─────────────────────────────────────────────────────────
    # Neo4j Helpers
    # ─────────────────────────────────────────────────────────

    async def _count_by_severity(
        self, repo: str, label: str
    ) -> dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MATCH (r:Repository {{full_name: $repo}})-[*1..2]->(n:{label})
                RETURN coalesce(n.severity, 'medium') AS sev, count(n) AS cnt
                """,
                repo=repo,
            )
            async for rec in result:
                sev = rec["sev"]
                if sev in counts:
                    counts[sev] = rec["cnt"]
        return counts

    async def _count_assets(self, repo: str) -> dict[str, int]:
        asset_types = [
            "File", "Module", "Class", "Function", "APIEndpoint",
            "Secret", "DatabaseConnection", "Infrastructure",
            "Container", "ExternalService", "Dependency",
        ]
        counts: dict[str, int] = {"total": 0}
        async with self._driver.session() as session:
            for at in asset_types:
                result = await session.run(
                    f"""
                    MATCH (r:Repository {{full_name: $repo}})-[*1..2]->(n:{at})
                    RETURN count(n) AS cnt
                    """,
                    repo=repo,
                )
                rec = await result.single()
                c = rec["cnt"] if rec else 0
                counts[at] = c
                counts["total"] += c
        return counts

    async def _count_attack_chains(self, repo: str) -> int:
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (ac:AttackChain {repo_full_name: $repo}) RETURN count(ac) AS cnt",
                repo=repo,
            )
            rec = await result.single()
            return rec["cnt"] if rec else 0

    async def _get_security_score(self, repo: str) -> int:
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (r:Repository {full_name: $repo}) RETURN r.security_score AS score",
                repo=repo,
            )
            rec = await result.single()
            return rec["score"] if rec and rec["score"] is not None else 50

    @staticmethod
    def _compute_risk_score(
        threats: dict[str, int],
        vulns: dict[str, int],
        chains: int,
    ) -> float:
        score = 0.0
        for sev, weight in SEV_WEIGHT.items():
            score += (threats.get(sev, 0) + vulns.get(sev, 0)) * weight
        score += chains * 0.5
        return round(min(10.0, score / 10.0), 3)
