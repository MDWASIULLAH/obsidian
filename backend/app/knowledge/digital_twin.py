"""
OBSIDIAN — AI Security Digital Twin Service.

Maintains a continuously-updated graph of every security-relevant
artefact in a repository: branches, commits, files, functions,
classes, dependencies, containers, IaC, secrets, cloud resources,
API endpoints, trust boundaries, auth flows, data flows, database
connections, and external services.

Every node carries: health, risk, confidence, security_score,
owner, last_modified, and type-specific properties.

All mutations use MERGE so the graph is always incrementally
updated — never fully rebuilt.
"""

from __future__ import annotations

import hashlib
from typing import Any

import structlog

from app.knowledge.graph import KnowledgeGraphService

logger = structlog.get_logger()


# ─────────────────────────────────────────────────────────────────
# Node type → colour / icon metadata (used by frontend)
# ─────────────────────────────────────────────────────────────────
NODE_TYPE_META: dict[str, dict] = {
    "Repository":         {"color": "#6366f1", "icon": "github"},
    "Branch":             {"color": "#8b5cf6", "icon": "git-branch"},
    "Commit":             {"color": "#a78bfa", "icon": "git-commit"},
    "File":               {"color": "#06b6d4", "icon": "file-code"},
    "Function":           {"color": "#0891b2", "icon": "function"},
    "Class":              {"color": "#0e7490", "icon": "layers"},
    "Module":             {"color": "#155e75", "icon": "package"},
    "Dependency":         {"color": "#f59e0b", "icon": "box"},
    "Container":          {"color": "#10b981", "icon": "container"},
    "DockerImage":        {"color": "#059669", "icon": "docker"},
    "TerraformResource":  {"color": "#6d28d9", "icon": "cloud"},
    "GitHubAction":       {"color": "#7c3aed", "icon": "zap"},
    "Secret":             {"color": "#ef4444", "icon": "key"},
    "CloudResource":      {"color": "#f97316", "icon": "cloud"},
    "APIEndpoint":        {"color": "#ec4899", "icon": "globe"},
    "TrustBoundary":      {"color": "#64748b", "icon": "shield"},
    "AuthFlow":           {"color": "#dc2626", "icon": "lock"},
    "DataFlow":           {"color": "#2563eb", "icon": "arrow-right"},
    "DatabaseConnection": {"color": "#7c3aed", "icon": "database"},
    "ExternalService":    {"color": "#d97706", "icon": "external-link"},
    "Infrastructure":     {"color": "#374151", "icon": "server"},
    "Vulnerability":      {"color": "#dc2626", "icon": "alert-triangle"},
    "Threat":             {"color": "#b91c1c", "icon": "skull"},
}


def _node_id(node_type: str, *parts: str) -> str:
    """Stable deterministic ID for a graph node."""
    raw = f"{node_type}::{':'.join(parts)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class DigitalTwinService:
    """
    Manages the AI Security Digital Twin in Neo4j.

    Each public method corresponds to one or more GitHub event types
    and performs idempotent (MERGE-based) graph mutations.
    """

    def __init__(self, graph: KnowledgeGraphService) -> None:
        self._graph = graph

    # ─────────────────────────────────────────────────────────────
    # Public event handlers
    # ─────────────────────────────────────────────────────────────

    async def process_push_event(
        self,
        repo_full_name: str,
        branch: str,
        commit_sha: str,
        sender: str,
        changed_files: list[str],
        payload: dict,
    ) -> dict[str, int]:
        """Handle a push event: upsert branch, commit, and file nodes."""
        stats = {"nodes_created": 0, "nodes_updated": 0, "edges_created": 0}
        async with self._graph._driver.session() as session:
            # Ensure repo node exists
            await session.run(
                "MERGE (r:Repository {full_name: $fn}) "
                "SET r.last_event = datetime(), r.last_modified = datetime()",
                fn=repo_full_name,
            )

            # Branch node
            branch_id = _node_id("Branch", repo_full_name, branch)
            await session.run(
                """
                MERGE (b:Branch {id: $id})
                SET b.name = $name,
                    b.repo_full_name = $fn,
                    b.last_push = datetime(),
                    b.pusher = $sender,
                    b.last_modified = datetime()
                WITH b
                MATCH (r:Repository {full_name: $fn})
                MERGE (r)-[:HAS_BRANCH]->(b)
                """,
                id=branch_id, name=branch, fn=repo_full_name, sender=sender,
            )
            stats["nodes_updated"] += 1

            # Commit node
            commit_id = _node_id("Commit", repo_full_name, commit_sha)
            head_commit = payload.get("head_commit") or {}
            await session.run(
                """
                MERGE (c:Commit {sha: $sha})
                SET c.id = $id,
                    c.repo_full_name = $fn,
                    c.message = $message,
                    c.author = $author,
                    c.timestamp = $ts,
                    c.last_modified = datetime()
                WITH c
                MATCH (b:Branch {id: $branch_id})
                MERGE (b)-[:HAS_COMMIT]->(c)
                """,
                sha=commit_sha,
                id=commit_id,
                fn=repo_full_name,
                message=(head_commit.get("message") or "")[:200],
                author=(head_commit.get("author") or {}).get("name", sender),
                ts=(head_commit.get("timestamp") or ""),
                branch_id=branch_id,
            )
            stats["nodes_created"] += 1

            # File nodes
            for file_path in changed_files:
                ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
                file_node_path = f"{repo_full_name}/{file_path}"
                await session.run(
                    """
                    MERGE (f:File {path: $path})
                    SET f.extension = $ext,
                        f.repo = $fn,
                        f.last_modified = datetime(),
                        f.last_commit = $sha
                    WITH f
                    MATCH (r:Repository {full_name: $fn})
                    MERGE (r)-[:CONTAINS]->(f)
                    WITH f
                    MATCH (c:Commit {sha: $sha})
                    MERGE (c)-[:MODIFIES]->(f)
                    """,
                    path=file_node_path,
                    ext=ext,
                    fn=repo_full_name,
                    sha=commit_sha,
                )
                stats["nodes_updated"] += 1

        logger.info("Digital Twin: push event processed",
                    repo=repo_full_name, files=len(changed_files))
        return stats

    async def process_pr_event(
        self,
        repo_full_name: str,
        pr_number: int,
        head_sha: str,
        head_branch: str,
        base_branch: str,
        action: str,
        sender: str,
    ) -> dict[str, int]:
        """Handle pull_request / pull_request_review events."""
        stats = {"nodes_created": 0, "nodes_updated": 0, "edges_created": 0}
        async with self._graph._driver.session() as session:
            head_branch_id = _node_id("Branch", repo_full_name, head_branch)
            base_branch_id = _node_id("Branch", repo_full_name, base_branch)

            # Ensure both branch nodes exist
            for bid, bname in [(head_branch_id, head_branch), (base_branch_id, base_branch)]:
                await session.run(
                    """
                    MERGE (b:Branch {id: $id})
                    SET b.name = $name, b.repo_full_name = $fn,
                        b.last_modified = datetime()
                    WITH b
                    MATCH (r:Repository {full_name: $fn})
                    MERGE (r)-[:HAS_BRANCH]->(b)
                    """,
                    id=bid, name=bname, fn=repo_full_name,
                )

            # PR relationship: head branch targets base branch
            pr_rel_props = {
                "pr_number": pr_number,
                "action": action,
                "author": sender,
                "head_sha": head_sha,
            }
            await session.run(
                """
                MATCH (head:Branch {id: $head_id})
                MATCH (base:Branch {id: $base_id})
                MERGE (head)-[pr:TARGETS]->(base)
                SET pr.pr_number = $pr_number,
                    pr.action = $action,
                    pr.author = $author,
                    pr.last_modified = datetime()
                """,
                head_id=head_branch_id,
                base_id=base_branch_id,
                **pr_rel_props,
            )
            stats["edges_created"] += 1

        logger.info("Digital Twin: PR event processed",
                    repo=repo_full_name, pr=pr_number, action=action)
        return stats

    async def process_branch_event(
        self,
        repo_full_name: str,
        branch: str,
        action: str,
    ) -> dict[str, int]:
        """Handle create/delete branch events."""
        async with self._graph._driver.session() as session:
            branch_id = _node_id("Branch", repo_full_name, branch)
            if action == "created":
                await session.run(
                    """
                    MERGE (b:Branch {id: $id})
                    SET b.name = $name, b.repo_full_name = $fn,
                        b.created_at = datetime(), b.last_modified = datetime()
                    WITH b
                    MATCH (r:Repository {full_name: $fn})
                    MERGE (r)-[:HAS_BRANCH]->(b)
                    """,
                    id=branch_id, name=branch, fn=repo_full_name,
                )
                return {"nodes_created": 1, "nodes_updated": 0, "edges_created": 1}
            else:  # deleted
                await session.run(
                    "MATCH (b:Branch {id: $id}) DETACH DELETE b",
                    id=branch_id,
                )
                return {"nodes_created": 0, "nodes_updated": 0, "edges_created": 0}

    async def process_security_alert(
        self,
        repo_full_name: str,
        event_type: str,
        alert: dict,
        action: str,
    ) -> dict[str, int]:
        """Handle security alert events (Dependabot, secret scanning, code scanning)."""
        async with self._graph._driver.session() as session:
            alert_id = str(alert.get("number") or alert.get("id") or "unknown")
            vuln_id = f"{event_type}::{repo_full_name}::{alert_id}"

            severity = (
                alert.get("security_vulnerability", {}).get("severity")
                or alert.get("rule", {}).get("severity")
                or "medium"
            )

            await session.run(
                """
                MERGE (v:Vulnerability {id: $id})
                SET v.title = $title,
                    v.severity = $severity,
                    v.source = $source,
                    v.action = $action,
                    v.last_modified = datetime()
                WITH v
                MATCH (r:Repository {full_name: $fn})
                MERGE (r)-[:HAS_VULNERABILITY]->(v)
                """,
                id=vuln_id,
                title=(
                    alert.get("security_advisory", {}).get("summary")
                    or alert.get("rule", {}).get("description")
                    or f"{event_type} alert {alert_id}"
                )[:255],
                severity=severity,
                source=event_type,
                action=action,
                fn=repo_full_name,
            )

            # If file info present (code scanning)
            if "most_recent_instance" in alert:
                loc = alert["most_recent_instance"].get("location", {})
                file_path = loc.get("path")
                if file_path:
                    full_path = f"{repo_full_name}/{file_path}"
                    await session.run(
                        """
                        MERGE (f:File {path: $path})
                        SET f.repo = $fn, f.last_modified = datetime()
                        WITH f
                        MATCH (v:Vulnerability {id: $vid})
                        MERGE (f)-[:HAS_VULNERABILITY]->(v)
                        """,
                        path=full_path, fn=repo_full_name, vid=vuln_id,
                    )

        return {"nodes_created": 1, "nodes_updated": 0, "edges_created": 1}

    async def process_deployment(
        self,
        repo_full_name: str,
        deployment: dict,
        action: str,
    ) -> dict[str, int]:
        """Handle deployment events — creates Container/Infrastructure nodes."""
        async with self._graph._driver.session() as session:
            deploy_id = str(deployment.get("id", ""))
            env = deployment.get("environment", "unknown")
            infra_id = _node_id("Infrastructure", repo_full_name, env)

            await session.run(
                """
                MERGE (i:Infrastructure {id: $id})
                SET i.environment = $env,
                    i.repo_full_name = $fn,
                    i.deploy_id = $deploy_id,
                    i.action = $action,
                    i.sha = $sha,
                    i.last_modified = datetime()
                WITH i
                MATCH (r:Repository {full_name: $fn})
                MERGE (r)-[:DEPLOYS]->(i)
                """,
                id=infra_id,
                env=env,
                fn=repo_full_name,
                deploy_id=deploy_id,
                action=action,
                sha=deployment.get("sha", ""),
            )

        return {"nodes_created": 1, "nodes_updated": 0, "edges_created": 1}

    async def process_workflow_run(
        self,
        repo_full_name: str,
        workflow_run: dict,
    ) -> dict[str, int]:
        """Handle workflow_run events — creates GitHubAction nodes."""
        async with self._graph._driver.session() as session:
            wf_id = _node_id("GitHubAction", repo_full_name, str(workflow_run.get("workflow_id", "")))
            await session.run(
                """
                MERGE (ga:GitHubAction {id: $id})
                SET ga.name = $name,
                    ga.repo_full_name = $fn,
                    ga.status = $status,
                    ga.conclusion = $conclusion,
                    ga.head_branch = $branch,
                    ga.head_sha = $sha,
                    ga.last_modified = datetime()
                WITH ga
                MATCH (r:Repository {full_name: $fn})
                MERGE (r)-[:TRIGGERS]->(ga)
                """,
                id=wf_id,
                name=workflow_run.get("name", "unknown"),
                fn=repo_full_name,
                status=workflow_run.get("status", ""),
                conclusion=workflow_run.get("conclusion") or "",
                branch=workflow_run.get("head_branch", ""),
                sha=workflow_run.get("head_sha", ""),
            )
        return {"nodes_created": 0, "nodes_updated": 1, "edges_created": 0}

    async def index_dependencies(
        self,
        repo_full_name: str,
        dependencies: dict[str, str],
    ) -> dict[str, int]:
        """Upsert dependency nodes (re-used from KnowledgeGraphService flow)."""
        async with self._graph._driver.session() as session:
            for dep_name, dep_version in dependencies.items():
                await session.run(
                    """
                    MERGE (d:Dependency {name: $name})
                    SET d.version = $version, d.last_modified = datetime()
                    WITH d
                    MATCH (r:Repository {full_name: $fn})
                    MERGE (r)-[:DEPENDS_ON]->(d)
                    """,
                    name=dep_name, version=dep_version, fn=repo_full_name,
                )
        return {"nodes_created": 0, "nodes_updated": len(dependencies), "edges_created": 0}

    # ─────────────────────────────────────────────────────────────
    # Read methods (for API endpoints)
    # ─────────────────────────────────────────────────────────────

    async def get_digital_twin(self, repo_full_name: str) -> dict[str, Any]:
        """Return the full twin graph for frontend Cytoscape rendering."""
        nodes: list[dict] = []
        edges: list[dict] = []
        node_counts: dict[str, int] = {}
        edge_counts: dict[str, int] = {}

        async with self._graph._driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Repository {full_name: $fn})-[rel*0..2]-(n)
                WHERE NOT n:Agent
                RETURN DISTINCT n, labels(n) AS lbls
                LIMIT 500
                """,
                fn=repo_full_name,
            )
            seen_ids: set[str] = set()
            async for record in result:
                node = record["n"]
                lbls: list[str] = record["lbls"]
                node_type = lbls[0] if lbls else "Unknown"
                node_id = str(node.element_id)
                if node_id in seen_ids:
                    continue
                seen_ids.add(node_id)
                props = dict(node)
                label = (
                    props.get("full_name")
                    or props.get("name")
                    or props.get("path")
                    or props.get("sha", "")[:8]
                    or node_id
                )
                nodes.append({
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "health": float(props.get("health", 1.0)),
                    "risk": float(props.get("risk", 0.0)),
                    "confidence": float(props.get("confidence", 1.0)),
                    "security_score": int(props.get("security_score", 100)),
                    "owner": props.get("owner"),
                    "last_modified": str(props.get("last_modified", "")),
                    "properties": {k: str(v) for k, v in props.items()
                                   if k not in ("health", "risk", "confidence", "security_score")},
                    **NODE_TYPE_META.get(node_type, {"color": "#6b7280", "icon": "circle"}),
                })
                node_counts[node_type] = node_counts.get(node_type, 0) + 1

            # Edges
            edge_result = await session.run(
                """
                MATCH (r:Repository {full_name: $fn})-[rel*0..2]-(n)
                MATCH (a)-[e]-(b)
                WHERE a.full_name = $fn OR b.full_name = $fn
                RETURN DISTINCT e, startNode(e) AS src, endNode(e) AS tgt
                LIMIT 1000
                """,
                fn=repo_full_name,
            )
            seen_edges: set[str] = set()
            async for record in edge_result:
                rel = record["e"]
                src_id = str(record["src"].element_id)
                tgt_id = str(record["tgt"].element_id)
                edge_key = f"{src_id}-{rel.type}-{tgt_id}"
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                edges.append({
                    "source": src_id,
                    "target": tgt_id,
                    "relationship": rel.type,
                    "properties": {},
                })
                edge_counts[rel.type] = edge_counts.get(rel.type, 0) + 1

        return {
            "repository_id": repo_full_name,
            "repository_name": repo_full_name,
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_counts": node_counts,
                "edge_counts": edge_counts,
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "overall_health": 1.0,
                "overall_risk": 0.0,
                "overall_security_score": 100,
            },
        }

    async def get_node_detail(
        self,
        node_id: str,
    ) -> dict[str, Any] | None:
        """Return a single node with its direct neighbors and connecting edges."""
        async with self._graph._driver.session() as session:
            result = await session.run(
                """
                MATCH (n) WHERE elementId(n) = $nid
                OPTIONAL MATCH (n)-[e]-(neighbor)
                RETURN n, labels(n) AS lbls,
                       collect(DISTINCT {
                           neighbor: neighbor,
                           neighbor_labels: labels(neighbor),
                           rel_type: type(e),
                           rel_dir: CASE WHEN startNode(e) = n THEN 'out' ELSE 'in' END
                       }) AS connections
                """,
                nid=node_id,
            )
            record = await result.single()
            if not record:
                return None

            node = record["n"]
            lbls = record["lbls"]
            node_type = lbls[0] if lbls else "Unknown"
            props = dict(node)

            neighbors = []
            edges_out = []
            for conn in record["connections"]:
                if conn["neighbor"] is None:
                    continue
                nb = conn["neighbor"]
                nb_type = conn["neighbor_labels"][0] if conn["neighbor_labels"] else "Unknown"
                nb_props = dict(nb)
                nb_label = (
                    nb_props.get("full_name")
                    or nb_props.get("name")
                    or nb_props.get("path")
                    or str(nb.element_id)
                )
                nb_id = str(nb.element_id)
                neighbors.append({
                    "id": nb_id,
                    "label": nb_label,
                    "type": nb_type,
                    "health": float(nb_props.get("health", 1.0)),
                    "risk": float(nb_props.get("risk", 0.0)),
                    "confidence": float(nb_props.get("confidence", 1.0)),
                    "security_score": int(nb_props.get("security_score", 100)),
                    "owner": nb_props.get("owner"),
                    "last_modified": str(nb_props.get("last_modified", "")),
                    "properties": {},
                    **NODE_TYPE_META.get(nb_type, {"color": "#6b7280", "icon": "circle"}),
                })
                if conn["rel_dir"] == "out":
                    edges_out.append({"source": node_id, "target": nb_id,
                                      "relationship": conn["rel_type"], "properties": {}})
                else:
                    edges_out.append({"source": nb_id, "target": node_id,
                                      "relationship": conn["rel_type"], "properties": {}})

            label = (
                props.get("full_name") or props.get("name")
                or props.get("path") or props.get("sha", "")[:8] or node_id
            )
            return {
                "node": {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "health": float(props.get("health", 1.0)),
                    "risk": float(props.get("risk", 0.0)),
                    "confidence": float(props.get("confidence", 1.0)),
                    "security_score": int(props.get("security_score", 100)),
                    "owner": props.get("owner"),
                    "last_modified": str(props.get("last_modified", "")),
                    "properties": {k: str(v) for k, v in props.items()},
                    **NODE_TYPE_META.get(node_type, {"color": "#6b7280", "icon": "circle"}),
                },
                "neighbors": neighbors,
                "edges": edges_out,
            }

    async def search_nodes(
        self,
        repo_full_name: str,
        query: str,
        limit: int = 50,
    ) -> list[dict]:
        """Full-text search over node labels/names within a repository."""
        async with self._graph._driver.session() as session:
            result = await session.run(
                """
                MATCH (n)
                WHERE (n.full_name CONTAINS $q OR n.name CONTAINS $q
                       OR n.path CONTAINS $q OR n.sha CONTAINS $q)
                  AND (n.repo_full_name = $fn OR n.full_name = $fn
                       OR n.repo = $fn OR n.full_name STARTS WITH $fn)
                RETURN n, labels(n) AS lbls
                LIMIT $limit
                """,
                q=query, fn=repo_full_name, limit=limit,
            )
            nodes = []
            async for record in result:
                node = record["n"]
                lbls = record["lbls"]
                node_type = lbls[0] if lbls else "Unknown"
                props = dict(node)
                label = (
                    props.get("full_name") or props.get("name")
                    or props.get("path") or str(node.element_id)
                )
                nodes.append({
                    "id": str(node.element_id),
                    "label": label,
                    "type": node_type,
                    "health": float(props.get("health", 1.0)),
                    "risk": float(props.get("risk", 0.0)),
                    "confidence": float(props.get("confidence", 1.0)),
                    "security_score": int(props.get("security_score", 100)),
                    "owner": props.get("owner"),
                    "last_modified": str(props.get("last_modified", "")),
                    "properties": {},
                    **NODE_TYPE_META.get(node_type, {"color": "#6b7280", "icon": "circle"}),
                })
        return nodes


# ── Singleton helper ──────────────────────────────────────────────

_service: DigitalTwinService | None = None


def get_digital_twin_service(graph: KnowledgeGraphService) -> DigitalTwinService:
    """Get or create the singleton DigitalTwinService."""
    global _service
    if _service is None:
        _service = DigitalTwinService(graph)
    return _service
