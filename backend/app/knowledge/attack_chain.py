"""
SENTINEL AI X — Attack Chain Engine.

Discovers and visualises multi-step attack paths by traversing
the Neo4j knowledge graph.  Each chain is an ordered sequence of
"hops" — from initial access through privilege escalation to impact.

Core concepts
─────────────
  AttackChain      Ordered list of ChainHop from entry to impact.
  ChainHop         One step: a node + the exploit/relationship used.
  BlastRadius      Set of nodes reachable from a compromised node.
  AttackMovie      Time-ordered chain with per-hop timing metadata
                   for the frontend cinematic replay.
"""

from __future__ import annotations

import hashlib
import json as _json
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

# ── MITRE kill-chain ordering (lower = earlier) ───────────────────
KILL_CHAIN_ORDER = {
    "reconnaissance": 0, "resource_development": 1,
    "initial_access": 2, "execution": 3,
    "persistence": 4, "privilege_escalation": 5,
    "defense_evasion": 6, "credential_access": 7,
    "discovery": 8, "lateral_movement": 9,
    "collection": 10, "command_and_control": 11,
    "exfiltration": 12, "impact": 13,
}

# ── Relationship types that indicate exploitable paths ────────────
EXPLOITABLE_RELS = {
    "HAS_VULNERABILITY", "HAS_THREAT", "DEPENDS_ON", "CALLS",
    "IMPORTS", "EXPOSES", "ACCESSES", "READS_FROM", "WRITES_TO",
    "CONNECTS_TO", "AUTHENTICATES_VIA", "FLOWS_TO", "RUNS_IN",
    "DEPLOYED_ON", "CONTAINS", "HAS_SECRET",
}


class AttackChainEngine:
    """
    Discovers attack chains by graph traversal in Neo4j.

    Uses variable-length path queries to find multi-step
    attack sequences, then scores and orders them by severity,
    chain length, and kill-chain progression.
    """

    def __init__(self, driver) -> None:
        self._driver = driver

    # ─────────────────────────────────────────────────────────
    # Schema
    # ─────────────────────────────────────────────────────────

    async def create_schema(self) -> None:
        stmts = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ac:AttackChain) REQUIRE ac.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (ac:AttackChain) ON (ac.repo_full_name)",
            "CREATE INDEX IF NOT EXISTS FOR (ac:AttackChain) ON (ac.severity_score)",
        ]
        async with self._driver.session() as session:
            for s in stmts:
                try:
                    await session.run(s)
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────
    # Chain Discovery
    # ─────────────────────────────────────────────────────────

    async def discover_chains(
        self,
        repo_full_name: str,
        max_depth: int = 6,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Discover attack chains starting from entry-point nodes
        (APIEndpoint, ExternalService, AuthFlow) through to
        high-value targets (Secret, DatabaseConnection, Infrastructure).

        Returns chains ordered by severity score (highest first).
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Repository {full_name: $repo})
                MATCH (entry)-[:EXPOSES|AUTHENTICATES_VIA|CONNECTS_TO*0..1]-(r)
                WHERE entry:APIEndpoint OR entry:ExternalService
                      OR entry:AuthFlow OR entry:TrustBoundary
                MATCH path = (entry)-[*1..$depth]-(target)
                WHERE target:Secret OR target:DatabaseConnection
                      OR target:Infrastructure OR target:Vulnerability
                      OR target:Threat
                AND length(path) >= 2
                AND ALL(n IN nodes(path) WHERE n.repo_full_name = $repo
                        OR n:Repository OR n:Vulnerability OR n:Threat)
                WITH path,
                     nodes(path) AS ns,
                     relationships(path) AS rs,
                     entry, target
                RETURN [n IN ns | {
                    id: coalesce(n.id, n.full_name, toString(id(n))),
                    label: coalesce(n.name, n.title, n.label, n.path,
                                    n.full_name, toString(id(n))),
                    type: labels(n)[0],
                    severity: n.severity,
                    mitre_phase: n.mitre_phase,
                    risk: coalesce(n.risk, 0.0),
                    security_score: coalesce(n.security_score, 50)
                }] AS chain_nodes,
                [r IN rs | {
                    type: type(r),
                    source: coalesce(startNode(r).id, toString(id(startNode(r)))),
                    target: coalesce(endNode(r).id, toString(id(endNode(r))))
                }] AS chain_edges,
                entry.id AS entry_id,
                target.id AS target_id,
                length(path) AS chain_length
                ORDER BY chain_length DESC
                LIMIT $limit
                """,
                repo=repo_full_name,
                depth=max_depth,
                limit=limit,
            )

            chains = []
            seen = set()
            async for rec in result:
                nodes = rec["chain_nodes"]
                edges = rec["chain_edges"]
                chain_length = rec["chain_length"]

                # Deduplicate by node-id sequence
                node_seq = tuple(n["id"] for n in nodes)
                if node_seq in seen:
                    continue
                seen.add(node_seq)

                # Score the chain
                severity_score = self._score_chain(nodes, edges, chain_length)
                chain_id = hashlib.sha256(
                    f"{repo_full_name}:{'->'.join(str(n['id']) for n in nodes)}".encode()
                ).hexdigest()[:16]

                # Build kill-chain phase progression
                phases = []
                for n in nodes:
                    phase = n.get("mitre_phase")
                    if phase and phase not in phases:
                        phases.append(phase)
                phases.sort(key=lambda p: KILL_CHAIN_ORDER.get(p, 99))

                chains.append({
                    "id": chain_id,
                    "repo_full_name": repo_full_name,
                    "entry_node": nodes[0] if nodes else None,
                    "target_node": nodes[-1] if nodes else None,
                    "nodes": nodes,
                    "edges": edges,
                    "chain_length": chain_length,
                    "severity_score": severity_score,
                    "kill_chain_phases": phases,
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                })

            # Sort by severity score descending
            chains.sort(key=lambda c: c["severity_score"], reverse=True)
            return chains[:limit]

    async def get_blast_radius(
        self,
        repo_full_name: str,
        node_id: str,
        max_depth: int = 4,
    ) -> dict[str, Any]:
        """
        Compute the blast radius from a compromised node.

        Returns all reachable nodes within max_depth hops,
        grouped by type and severity.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (start {id: $nid})
                WHERE start.repo_full_name = $repo
                      OR start:Repository
                MATCH path = (start)-[*1..$depth]-(reached)
                WHERE reached <> start
                WITH DISTINCT reached,
                     min(length(path)) AS distance
                RETURN reached.id AS id,
                       coalesce(reached.name, reached.title,
                                reached.label, reached.path,
                                toString(id(reached))) AS label,
                       labels(reached)[0] AS type,
                       reached.severity AS severity,
                       coalesce(reached.risk, 0.0) AS risk,
                       coalesce(reached.security_score, 50) AS security_score,
                       distance
                ORDER BY distance ASC, risk DESC
                LIMIT 100
                """,
                nid=node_id, repo=repo_full_name, depth=max_depth,
            )
            nodes = []
            type_counts: dict[str, int] = {}
            severity_counts: dict[str, int] = {}
            async for rec in result:
                d = dict(rec)
                nodes.append(d)
                t = d.get("type", "Unknown")
                type_counts[t] = type_counts.get(t, 0) + 1
                sev = d.get("severity") or "unknown"
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "origin_node_id": node_id,
            "repo_full_name": repo_full_name,
            "total_reachable": len(nodes),
            "nodes": nodes,
            "type_distribution": type_counts,
            "severity_distribution": severity_counts,
            "max_depth": max_depth,
        }

    async def build_attack_movie(
        self,
        chain: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Transform a discovered attack chain into a time-sequenced
        "movie" with per-hop metadata for cinematic replay.

        Each frame represents one attacker action.
        """
        nodes = chain.get("nodes", [])
        edges = chain.get("edges", [])
        frames = []

        for i, node in enumerate(nodes):
            phase = node.get("mitre_phase") or "unknown"
            phase_order = KILL_CHAIN_ORDER.get(phase, 99)

            frame = {
                "sequence": i,
                "node": node,
                "edge": edges[i - 1] if i > 0 and i <= len(edges) else None,
                "action": self._describe_hop(
                    nodes[i - 1] if i > 0 else None, node,
                    edges[i - 1] if i > 0 and i <= len(edges) else None,
                ),
                "kill_chain_phase": phase,
                "kill_chain_order": phase_order,
                "severity_at_hop": node.get("severity") or "medium",
                "cumulative_risk": min(1.0, sum(
                    (n.get("risk") or 0.0) for n in nodes[:i + 1]
                ) / max(1, i + 1)),
                "delay_ms": 1500 + (phase_order * 200),
            }
            frames.append(frame)

        return {
            "chain_id": chain.get("id"),
            "title": f"Attack: {nodes[0]['label'] if nodes else '?'} → {nodes[-1]['label'] if nodes else '?'}",
            "total_frames": len(frames),
            "total_duration_ms": sum(f["delay_ms"] for f in frames),
            "severity_score": chain.get("severity_score", 0),
            "kill_chain_phases": chain.get("kill_chain_phases", []),
            "frames": frames,
        }

    async def persist_chain(
        self, chain: dict[str, Any]
    ) -> str:
        """Store a discovered chain as an AttackChain node in Neo4j."""
        chain_id = chain["id"]
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (ac:AttackChain {id: $cid})
                SET ac.repo_full_name = $repo,
                    ac.severity_score = $score,
                    ac.chain_length = $length,
                    ac.kill_chain_phases = $phases,
                    ac.entry_label = $entry,
                    ac.target_label = $target,
                    ac.nodes_json = $njson,
                    ac.edges_json = $ejson,
                    ac.discovered_at = datetime()
                """,
                cid=chain_id,
                repo=chain["repo_full_name"],
                score=chain["severity_score"],
                length=chain["chain_length"],
                phases=chain.get("kill_chain_phases", []),
                entry=chain["entry_node"]["label"] if chain.get("entry_node") else "",
                target=chain["target_node"]["label"] if chain.get("target_node") else "",
                njson=_json.dumps(chain["nodes"]),
                ejson=_json.dumps(chain["edges"]),
            )
        return chain_id

    async def get_persisted_chains(
        self, repo_full_name: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Retrieve previously discovered and persisted chains."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (ac:AttackChain {repo_full_name: $repo})
                RETURN ac.id AS id,
                       ac.severity_score AS severity_score,
                       ac.chain_length AS chain_length,
                       ac.kill_chain_phases AS kill_chain_phases,
                       ac.entry_label AS entry_label,
                       ac.target_label AS target_label,
                       ac.nodes_json AS nodes_json,
                       ac.edges_json AS edges_json,
                       ac.discovered_at AS discovered_at
                ORDER BY ac.severity_score DESC
                LIMIT $limit
                """,
                repo=repo_full_name, limit=limit,
            )
            chains = []
            async for rec in result:
                d = dict(rec)
                try:
                    d["nodes"] = _json.loads(d.pop("nodes_json") or "[]")
                    d["edges"] = _json.loads(d.pop("edges_json") or "[]")
                except Exception:
                    d["nodes"] = []
                    d["edges"] = []
                d["entry_node"] = d["nodes"][0] if d["nodes"] else None
                d["target_node"] = d["nodes"][-1] if d["nodes"] else None
                d["repo_full_name"] = repo_full_name
                chains.append(d)
            return chains

    # ─────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _score_chain(
        nodes: list[dict], edges: list[dict], length: int
    ) -> float:
        """
        Score = (sum of node risks) × length_factor × phase_progression_factor.
        """
        sev_map = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
        risk_sum = 0.0
        for n in nodes:
            risk_sum += n.get("risk") or sev_map.get(n.get("severity", "low"), 0.25)

        length_factor = min(2.0, 1.0 + (length - 1) * 0.15)

        # Phase progression bonus — chains that move through kill-chain
        phases_seen = set()
        for n in nodes:
            p = n.get("mitre_phase")
            if p:
                phases_seen.add(p)
        phase_factor = 1.0 + len(phases_seen) * 0.1

        return round(risk_sum * length_factor * phase_factor, 3)

    @staticmethod
    def _describe_hop(
        prev: dict | None, curr: dict, edge: dict | None
    ) -> str:
        """Generate a human-readable description of an attack hop."""
        if prev is None:
            return f"Attacker identifies entry point: {curr.get('label', '?')} ({curr.get('type', '?')})"

        rel = edge.get("type", "CONNECTED_TO") if edge else "reaches"
        verb_map = {
            "HAS_VULNERABILITY": "exploits vulnerability in",
            "DEPENDS_ON": "pivots through dependency of",
            "CALLS": "hijacks call from",
            "IMPORTS": "compromises import in",
            "EXPOSES": "accesses exposed",
            "ACCESSES": "gains access to",
            "READS_FROM": "exfiltrates data from",
            "WRITES_TO": "injects malicious data into",
            "CONNECTS_TO": "establishes connection to",
            "AUTHENTICATES_VIA": "bypasses authentication on",
            "FLOWS_TO": "intercepts data flowing to",
            "RUNS_IN": "escapes into",
            "DEPLOYED_ON": "compromises deployment of",
            "CONTAINS": "moves laterally into",
            "HAS_SECRET": "steals secret from",
            "HAS_THREAT": "chains threat in",
        }
        verb = verb_map.get(rel, f"reaches via {rel}")
        return f"From {prev.get('label', '?')}, attacker {verb} {curr.get('label', '?')}"
