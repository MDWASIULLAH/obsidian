"""
OBSIDIAN — Threat Evolution Engine.

Tracks how security threats mutate and evolve over time.
Stores temporal snapshots in Neo4j and uses NVIDIA NIM to
predict future attack trajectories.

Core concepts:
  - ThreatSnapshot: point-in-time state of a threat
  - EvolutionTimeline: ordered series of snapshots
  - PredictedTrajectory: LLM-predicted future states
  - ExploitabilityScore: how likely to be weaponized soon
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


# ── Severity → numeric weight ─────────────────────────────────────
SEVERITY_WEIGHT = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25, "info": 0.0}

# ── MITRE ATT&CK technique → phase ───────────────────────────────
MITRE_PHASE = {
    "T1190": "initial_access", "T1059": "execution", "T1078": "initial_access",
    "T1053": "persistence", "T1547": "persistence", "T1055": "privilege_escalation",
    "T1068": "privilege_escalation", "T1110": "credential_access", "T1552": "credential_access",
    "T1486": "impact", "T1496": "impact", "T1567": "exfiltration",
}


class ThreatEvolutionEngine:
    """
    Maintains a temporal graph of threat evolution in Neo4j.

    For each vulnerability/threat node it stores timestamped
    snapshots (ThreatSnapshot) and computes evolution metrics:
      - velocity: rate of severity change
      - exploitability_delta: how quickly it becomes exploitable
      - predicted_peak: when we expect peak risk
      - remediation_urgency: 0-1 score for prioritisation
    """

    def __init__(self, driver) -> None:
        self._driver = driver

    # ─────────────────────────────────────────────────────────────
    # Schema
    # ─────────────────────────────────────────────────────────────

    async def create_schema(self) -> None:
        """Create ThreatSnapshot constraints and timeline indexes."""
        stmts = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ts:ThreatSnapshot) REQUIRE ts.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (tl:ThreatTimeline) REQUIRE tl.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (pt:PredictedTrajectory) REQUIRE pt.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (ts:ThreatSnapshot) ON (ts.threat_id)",
            "CREATE INDEX IF NOT EXISTS FOR (ts:ThreatSnapshot) ON (ts.captured_at)",
            "CREATE INDEX IF NOT EXISTS FOR (ts:ThreatSnapshot) ON (ts.repo_full_name)",
        ]
        async with self._driver.session() as session:
            for stmt in stmts:
                try:
                    await session.run(stmt)
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────────
    # Snapshot Recording
    # ─────────────────────────────────────────────────────────────

    async def record_threat_snapshot(
        self,
        repo_full_name: str,
        threat_id: str,
        title: str,
        severity: str,
        category: str,
        cwe_id: str | None,
        cve_id: str | None,
        mitre_technique: str | None,
        confidence: float,
        file_path: str | None,
        agent_name: str,
        additional_props: dict | None = None,
    ) -> str:
        """
        Record a point-in-time snapshot of a threat.

        Returns the snapshot node ID. Called every time an agent
        discovers or re-evaluates a threat.
        """
        now = datetime.now(timezone.utc).isoformat()
        snap_id = hashlib.sha256(
            f"{threat_id}:{now}:{severity}".encode()
        ).hexdigest()[:20]

        severity_score = SEVERITY_WEIGHT.get(severity.lower(), 0.25)
        mitre_phase = MITRE_PHASE.get(mitre_technique or "", "unknown")
        props = additional_props or {}

        async with self._driver.session() as session:
            # Upsert the parent Threat node
            await session.run(
                """
                MERGE (t:Threat {id: $tid})
                SET t.title = $title,
                    t.severity = $severity,
                    t.category = $category,
                    t.cwe_id = $cwe,
                    t.cve_id = $cve,
                    t.mitre_technique = $mitre,
                    t.mitre_phase = $phase,
                    t.last_seen = datetime(),
                    t.repo_full_name = $repo
                WITH t
                MATCH (r:Repository {full_name: $repo})
                MERGE (r)-[:HAS_THREAT]->(t)
                """,
                tid=threat_id, title=title, severity=severity, category=category,
                cwe=cwe_id, cve=cve_id, mitre=mitre_technique, phase=mitre_phase,
                repo=repo_full_name,
            )

            # Create snapshot node
            await session.run(
                """
                CREATE (s:ThreatSnapshot {
                    id: $sid,
                    threat_id: $tid,
                    repo_full_name: $repo,
                    severity: $severity,
                    severity_score: $score,
                    confidence: $confidence,
                    file_path: $fpath,
                    agent_name: $agent,
                    captured_at: datetime(),
                    captured_at_iso: $now,
                    mitre_technique: $mitre,
                    mitre_phase: $phase
                })
                WITH s
                MATCH (t:Threat {id: $tid})
                CREATE (t)-[:HAS_SNAPSHOT {at: datetime()}]->(s)
                """,
                sid=snap_id, tid=threat_id, repo=repo_full_name,
                severity=severity, score=severity_score, confidence=confidence,
                fpath=file_path, agent=agent_name, now=now,
                mitre=mitre_technique, phase=mitre_phase,
            )

            # Ensure ThreatTimeline node exists and link snapshot
            timeline_id = hashlib.sha256(
                f"timeline:{repo_full_name}:{threat_id}".encode()
            ).hexdigest()[:16]
            await session.run(
                """
                MERGE (tl:ThreatTimeline {id: $tlid})
                SET tl.threat_id = $tid,
                    tl.repo_full_name = $repo,
                    tl.updated_at = datetime()
                WITH tl
                MATCH (s:ThreatSnapshot {id: $sid})
                CREATE (tl)-[:INCLUDES {sequence: timestamp()}]->(s)
                WITH tl
                MATCH (r:Repository {full_name: $repo})
                MERGE (r)-[:HAS_TIMELINE]->(tl)
                """,
                tlid=timeline_id, tid=threat_id, repo=repo_full_name, sid=snap_id,
            )

        logger.info("Threat snapshot recorded", threat_id=threat_id, severity=severity)
        return snap_id

    # ─────────────────────────────────────────────────────────────
    # Evolution Metrics
    # ─────────────────────────────────────────────────────────────

    async def get_evolution_timeline(
        self,
        repo_full_name: str,
        threat_id: str,
        limit: int = 30,
    ) -> dict[str, Any]:
        """
        Return the ordered evolution timeline for a threat.

        Includes computed velocity and trend direction.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (t:Threat {id: $tid, repo_full_name: $repo})
                -[:HAS_SNAPSHOT]->(s:ThreatSnapshot)
                RETURN s.id AS id,
                       s.severity AS severity,
                       s.severity_score AS score,
                       s.confidence AS confidence,
                       s.captured_at_iso AS captured_at,
                       s.agent_name AS agent,
                       s.file_path AS file_path,
                       s.mitre_technique AS mitre,
                       s.mitre_phase AS phase
                ORDER BY s.captured_at ASC
                LIMIT $limit
                """,
                tid=threat_id, repo=repo_full_name, limit=limit,
            )
            snapshots = []
            async for rec in result:
                snapshots.append(dict(rec))

            # Fetch threat metadata
            meta_result = await session.run(
                """
                MATCH (t:Threat {id: $tid})
                RETURN t.title AS title, t.severity AS severity,
                       t.cwe_id AS cwe, t.cve_id AS cve,
                       t.mitre_technique AS mitre, t.category AS category,
                       t.last_seen AS last_seen
                """,
                tid=threat_id,
            )
            meta = {}
            meta_rec = await meta_result.single()
            if meta_rec:
                meta = dict(meta_rec)

        # Compute velocity (change in severity score per snapshot)
        velocity = 0.0
        trend = "stable"
        if len(snapshots) >= 2:
            scores = [s["score"] or 0.0 for s in snapshots]
            deltas = [scores[i + 1] - scores[i] for i in range(len(scores) - 1)]
            velocity = sum(deltas) / len(deltas) if deltas else 0.0
            if velocity > 0.05:
                trend = "escalating"
            elif velocity < -0.05:
                trend = "improving"

        return {
            "threat_id": threat_id,
            "repo": repo_full_name,
            "metadata": meta,
            "snapshots": snapshots,
            "snapshot_count": len(snapshots),
            "velocity": round(velocity, 4),
            "trend": trend,
            "first_seen": snapshots[0]["captured_at"] if snapshots else None,
            "last_seen": snapshots[-1]["captured_at"] if snapshots else None,
        }

    async def get_all_timelines(self, repo_full_name: str) -> list[dict[str, Any]]:
        """Return summary timelines for all threats in a repository."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Repository {full_name: $repo})-[:HAS_THREAT]->(t:Threat)
                OPTIONAL MATCH (t)-[:HAS_SNAPSHOT]->(s:ThreatSnapshot)
                WITH t, count(s) AS snap_count,
                     collect(s.severity_score) AS scores,
                     min(s.captured_at_iso) AS first_seen,
                     max(s.captured_at_iso) AS last_seen
                RETURN t.id AS threat_id,
                       t.title AS title,
                       t.severity AS severity,
                       t.category AS category,
                       t.cwe_id AS cwe,
                       t.cve_id AS cve,
                       t.mitre_technique AS mitre,
                       t.mitre_phase AS phase,
                       snap_count,
                       scores,
                       first_seen,
                       last_seen
                ORDER BY t.severity DESC
                LIMIT 100
                """,
                repo=repo_full_name,
            )
            timelines = []
            async for rec in result:
                d = dict(rec)
                scores = d.pop("scores") or []
                velocity = 0.0
                trend = "stable"
                if len(scores) >= 2:
                    deltas = [scores[i + 1] - scores[i] for i in range(len(scores) - 1)]
                    velocity = sum(deltas) / len(deltas)
                    trend = "escalating" if velocity > 0.05 else ("improving" if velocity < -0.05 else "stable")
                d["velocity"] = round(velocity, 4)
                d["trend"] = trend
                d["latest_score"] = scores[-1] if scores else 0.0
                timelines.append(d)
        return timelines

    async def record_predicted_trajectory(
        self,
        threat_id: str,
        repo_full_name: str,
        predictions: list[dict],
        model_used: str,
        confidence: float,
    ) -> str:
        """Store an LLM-generated future trajectory for a threat."""
        import json as _json
        pt_id = hashlib.sha256(
            f"pt:{threat_id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (pt:PredictedTrajectory {id: $ptid})
                SET pt.threat_id = $tid,
                    pt.repo_full_name = $repo,
                    pt.predictions_json = $pjson,
                    pt.model_used = $model,
                    pt.confidence = $conf,
                    pt.created_at = datetime()
                WITH pt
                MATCH (t:Threat {id: $tid})
                MERGE (t)-[:HAS_PREDICTION]->(pt)
                """,
                ptid=pt_id, tid=threat_id, repo=repo_full_name,
                pjson=_json.dumps(predictions), model=model_used, conf=confidence,
            )
        return pt_id

    async def get_latest_prediction(
        self, threat_id: str
    ) -> dict[str, Any] | None:
        """Return the most recent predicted trajectory for a threat."""
        import json as _json
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (t:Threat {id: $tid})-[:HAS_PREDICTION]->(pt:PredictedTrajectory)
                RETURN pt.id AS id, pt.predictions_json AS pjson,
                       pt.model_used AS model, pt.confidence AS confidence,
                       pt.created_at AS created_at
                ORDER BY pt.created_at DESC
                LIMIT 1
                """,
                tid=threat_id,
            )
            rec = await result.single()
            if not rec:
                return None
            d = dict(rec)
            try:
                d["predictions"] = _json.loads(d.pop("pjson") or "[]")
            except Exception:
                d["predictions"] = []
            return d

    async def get_exploitability_rankings(
        self, repo_full_name: str, top_n: int = 20
    ) -> list[dict[str, Any]]:
        """
        Rank threats by exploitability urgency.

        Score = severity_weight × velocity_factor × recency_factor
        Higher score = needs remediation soonest.
        """
        timelines = await self.get_all_timelines(repo_full_name)
        ranked = []
        for tl in timelines:
            base = SEVERITY_WEIGHT.get(tl.get("severity", "low"), 0.25)
            velocity_factor = 1.0 + max(0.0, tl.get("velocity", 0.0)) * 2
            snap_count = tl.get("snap_count", 0) or 0
            recency_factor = min(1.5, 1.0 + snap_count * 0.05)
            urgency = round(base * velocity_factor * recency_factor, 4)
            ranked.append({**tl, "urgency_score": urgency})

        ranked.sort(key=lambda x: x["urgency_score"], reverse=True)
        return ranked[:top_n]
