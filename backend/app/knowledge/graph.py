"""
SENTINEL AI X — Neo4j Security Knowledge Graph.

Manages the full knowledge graph with nodes for repositories,
files, functions, classes, dependencies, vulnerabilities,
threats, and their relationships.

Node types: Repository, File, Function, Class, Secret,
            Dependency, Threat, Vulnerability, CloudResource,
            Container, Fix, Test, Agent

Edge types: imports, calls, depends_on, contains_secret,
            can_attack, fixed_by, verified_by, chained_to,
            mitigates, belongs_to
"""

from __future__ import annotations

from typing import Any

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import get_settings

logger = structlog.get_logger()


class KnowledgeGraphService:
    """
    Neo4j-backed security knowledge graph.

    Provides methods to create, query, and traverse the graph
    for attack path discovery and agent context enrichment.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._driver: AsyncDriver | None = None
        self._uri = settings.neo4j_uri
        self._user = settings.neo4j_user
        self._password = settings.neo4j_password

    async def initialize(self) -> None:
        """Connect to Neo4j and create constraints/indexes."""
        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
        )
        # Verify connectivity
        async with self._driver.session() as session:
            await session.run("RETURN 1")

        await self._create_schema()

        # Initialize Threat Evolution schema alongside the main graph
        try:
            from app.knowledge.threat_evolution import ThreatEvolutionEngine
            te = ThreatEvolutionEngine(self._driver)
            await te.create_schema()
        except Exception as exc:
            logger.warning("Threat Evolution schema init skipped", error=str(exc))

        # Initialize Attack Chain schema
        try:
            from app.knowledge.attack_chain import AttackChainEngine
            ac = AttackChainEngine(self._driver)
            await ac.create_schema()
        except Exception as exc:
            logger.warning("Attack Chain schema init skipped", error=str(exc))

        # Initialize Security Timeline schema
        try:
            from app.knowledge.security_timeline import SecurityTimelineEngine
            st = SecurityTimelineEngine(self._driver)
            await st.create_schema()
        except Exception as exc:
            logger.warning("Security Timeline schema init skipped", error=str(exc))

        logger.info("Neo4j Knowledge Graph initialized")


    async def close(self) -> None:
        """Close the Neo4j driver."""
        if self._driver:
            await self._driver.close()

    # ═══════════════════════════════════════════════════════════
    # Schema
    # ═══════════════════════════════════════════════════════════

    async def _create_schema(self) -> None:
        """Create constraints and indexes for all node types."""
        statements = [
            # ── Core Security Nodes (original) ──────────────────────
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repository) REQUIRE r.full_name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Dependency) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vulnerability) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Threat) REQUIRE t.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (f:Function) ON (f.name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (s:Secret) ON (s.type)",
            "CREATE INDEX IF NOT EXISTS FOR (a:Agent) ON (a.name)",
            # ── Digital Twin Node Types ──────────────────────────────
            "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Branch) REQUIRE b.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Commit) REQUIRE c.sha IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Module) REQUIRE m.path IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ct:Container) REQUIRE ct.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (di:DockerImage) REQUIRE di.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (tf:TerraformResource) REQUIRE tf.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ga:GitHubAction) REQUIRE ga.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (cr:CloudResource) REQUIRE cr.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ae:APIEndpoint) REQUIRE ae.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (tb:TrustBoundary) REQUIRE tb.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (af:AuthFlow) REQUIRE af.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (df:DataFlow) REQUIRE df.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (db:DatabaseConnection) REQUIRE db.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (es:ExternalService) REQUIRE es.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Infrastructure) REQUIRE i.id IS UNIQUE",
            # ── Digital Twin Performance Indexes ─────────────────────
            "CREATE INDEX IF NOT EXISTS FOR (b:Branch) ON (b.repo_full_name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Commit) ON (c.repo_full_name)",
            "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.repo)",
            "CREATE INDEX IF NOT EXISTS FOR (v:Vulnerability) ON (v.severity)",
        ]
        async with self._driver.session() as session:
            for stmt in statements:
                try:
                    await session.run(stmt)
                except Exception as e:
                    logger.debug("Schema statement skipped", stmt=stmt[:60], error=str(e))

    # ═══════════════════════════════════════════════════════════
    # Repository Indexing
    # ═══════════════════════════════════════════════════════════

    async def index_repository(
        self,
        full_name: str,
        files: list[str],
        dependencies: dict[str, str],
    ) -> None:
        """
        Index a repository into the knowledge graph.

        Creates Repository, File, and Dependency nodes with relationships.
        """
        async with self._driver.session() as session:
            # Create/update repository node
            await session.run(
                """
                MERGE (r:Repository {full_name: $full_name})
                SET r.last_indexed = datetime(),
                    r.file_count = $file_count
                """,
                full_name=full_name,
                file_count=len(files),
            )

            # Create file nodes
            for file_path in files:
                ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
                await session.run(
                    """
                    MERGE (f:File {path: $path})
                    SET f.extension = $ext, f.repo = $repo
                    WITH f
                    MATCH (r:Repository {full_name: $repo})
                    MERGE (r)-[:CONTAINS]->(f)
                    """,
                    path=f"{full_name}/{file_path}",
                    ext=ext,
                    repo=full_name,
                )

            # Create dependency nodes
            for dep_name, dep_version in dependencies.items():
                await session.run(
                    """
                    MERGE (d:Dependency {name: $name})
                    SET d.version = $version
                    WITH d
                    MATCH (r:Repository {full_name: $repo})
                    MERGE (r)-[:DEPENDS_ON]->(d)
                    """,
                    name=dep_name,
                    version=dep_version,
                    repo=full_name,
                )

        logger.info(
            "Repository indexed in knowledge graph",
            repo=full_name,
            files=len(files),
            deps=len(dependencies),
        )

    # ═══════════════════════════════════════════════════════════
    # Vulnerability & Threat Management
    # ═══════════════════════════════════════════════════════════

    async def add_vulnerability(
        self,
        vuln_id: str,
        title: str,
        severity: str,
        cwe_id: str | None = None,
        file_path: str | None = None,
        agent_name: str | None = None,
    ) -> None:
        """Add a vulnerability node and connect to affected file."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (v:Vulnerability {id: $id})
                SET v.title = $title,
                    v.severity = $severity,
                    v.cwe_id = $cwe_id,
                    v.discovered_at = datetime()
                """,
                id=vuln_id,
                title=title,
                severity=severity,
                cwe_id=cwe_id,
            )

            if file_path:
                await session.run(
                    """
                    MATCH (v:Vulnerability {id: $vid})
                    MATCH (f:File {path: $fpath})
                    MERGE (f)-[:HAS_VULNERABILITY]->(v)
                    """,
                    vid=vuln_id,
                    fpath=file_path,
                )

            if agent_name:
                await session.run(
                    """
                    MERGE (a:Agent {name: $agent})
                    WITH a
                    MATCH (v:Vulnerability {id: $vid})
                    MERGE (a)-[:DISCOVERED]->(v)
                    """,
                    agent=agent_name,
                    vid=vuln_id,
                )

    async def add_threat(
        self,
        threat_id: str,
        title: str,
        stride_category: str,
        severity: str,
        mitre_technique: str | None = None,
    ) -> None:
        """Add a threat node to the graph."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (t:Threat {id: $id})
                SET t.title = $title,
                    t.stride_category = $category,
                    t.severity = $severity,
                    t.mitre_technique = $mitre
                """,
                id=threat_id,
                title=title,
                category=stride_category,
                severity=severity,
                mitre=mitre_technique,
            )

    async def add_fix(
        self,
        vuln_id: str,
        fix_id: str,
        patch_file: str,
        description: str,
    ) -> None:
        """Record that a vulnerability was fixed."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (fix:Fix {id: $fix_id})
                SET fix.patch_file = $patch_file,
                    fix.description = $description,
                    fix.created_at = datetime()
                WITH fix
                MATCH (v:Vulnerability {id: $vid})
                MERGE (v)-[:FIXED_BY]->(fix)
                """,
                fix_id=fix_id,
                patch_file=patch_file,
                description=description,
                vid=vuln_id,
            )

    # ═══════════════════════════════════════════════════════════
    # Attack Path Discovery
    # ═══════════════════════════════════════════════════════════

    async def find_attack_paths(
        self,
        repo_full_name: str,
        max_depth: int = 5,
    ) -> list[dict]:
        """
        Find attack paths through the knowledge graph.

        Traverses vulnerability → file → dependency chains
        to identify how an attacker could progress.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH path = (v:Vulnerability)-[*1..$depth]-(target)
                WHERE EXISTS {
                    MATCH (r:Repository {full_name: $repo})-[:CONTAINS]->(f:File)
                    -[:HAS_VULNERABILITY]->(v)
                }
                RETURN path
                LIMIT 50
                """,
                repo=repo_full_name,
                depth=max_depth,
            )

            paths = []
            async for record in result:
                path = record["path"]
                nodes = [
                    {"labels": list(n.labels), "properties": dict(n)}
                    for n in path.nodes
                ]
                edges = [
                    {"type": r.type, "properties": dict(r)}
                    for r in path.relationships
                ]
                paths.append({"nodes": nodes, "edges": edges})

            return paths

    # ═══════════════════════════════════════════════════════════
    # Query Helpers
    # ═══════════════════════════════════════════════════════════

    async def get_repository_context(self, repo_full_name: str) -> dict[str, Any]:
        """Get full graph context for a repository."""
        async with self._driver.session() as session:
            # Get vulnerability summary
            vuln_result = await session.run(
                """
                MATCH (r:Repository {full_name: $repo})-[:CONTAINS]->(f:File)
                -[:HAS_VULNERABILITY]->(v:Vulnerability)
                RETURN v.severity AS severity, count(v) AS count
                """,
                repo=repo_full_name,
            )
            vuln_counts = {}
            async for record in vuln_result:
                vuln_counts[record["severity"]] = record["count"]

            # Get dependency count
            dep_result = await session.run(
                """
                MATCH (r:Repository {full_name: $repo})-[:DEPENDS_ON]->(d:Dependency)
                RETURN count(d) AS dep_count
                """,
                repo=repo_full_name,
            )
            dep_record = await dep_result.single()
            dep_count = dep_record["dep_count"] if dep_record else 0

            return {
                "repository": repo_full_name,
                "vulnerability_summary": vuln_counts,
                "dependency_count": dep_count,
            }

    async def get_graph_visualization(self, repo_full_name: str) -> dict:
        """Get nodes and edges for frontend visualization."""
        nodes = []
        edges = []

        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Repository {full_name: $repo})-[rel]-(connected)
                RETURN r, rel, connected
                LIMIT 200
                """,
                repo=repo_full_name,
            )

            seen_nodes = set()
            async for record in result:
                for node_key in ["r", "connected"]:
                    node = record[node_key]
                    node_id = str(node.element_id)
                    if node_id not in seen_nodes:
                        seen_nodes.add(node_id)
                        nodes.append({
                            "id": node_id,
                            "label": dict(node).get("full_name", dict(node).get("name", dict(node).get("path", ""))),
                            "type": list(node.labels)[0] if node.labels else "Unknown",
                            "properties": dict(node),
                        })

                rel = record["rel"]
                edges.append({
                    "source": str(rel.start_node.element_id),
                    "target": str(rel.end_node.element_id),
                    "relationship": rel.type,
                })

        return {"nodes": nodes, "edges": edges}

    async def clear_repository(self, repo_full_name: str) -> None:
        """Remove all graph data for a repository."""
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (r:Repository {full_name: $repo})-[*0..3]-(connected)
                DETACH DELETE connected
                """,
                repo=repo_full_name,
            )
            await session.run(
                "MATCH (r:Repository {full_name: $repo}) DETACH DELETE r",
                repo=repo_full_name,
            )
