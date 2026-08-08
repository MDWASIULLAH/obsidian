"""
OBSIDIAN — LangGraph Pipeline State.

Defines the shared state that flows through the multi-agent
LangGraph pipeline. Each agent reads from and writes to this
state, which is persisted via PostgreSQL checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any

from langgraph.graph import add_messages


# ═══════════════════════════════════════════════════════════════════
# Pipeline State
# ═══════════════════════════════════════════════════════════════════


@dataclass
class PipelineState:
    """
    The shared mutable state for the entire security pipeline.

    LangGraph passes this between nodes. Each agent node reads
    what it needs and writes its outputs.

    Annotations:
      - `add_messages` reducer appends instead of replacing
    """

    # ── Input Context ──────────────────────────────────────────
    # Set at pipeline start, read-only for agents
    repository_id: str = ""
    repository_full_name: str = ""
    commit_sha: str = ""
    branch: str = ""
    scan_id: str = ""
    trigger: str = "push"  # push | pull_request | manual
    pr_number: int | None = None

    # ── Repository Data ────────────────────────────────────────
    # Populated during indexing phase
    diff_content: str = ""
    changed_files: list[str] = field(default_factory=list)
    file_contents: dict[str, str] = field(default_factory=dict)
    repo_languages: list[str] = field(default_factory=list)
    repo_frameworks: list[str] = field(default_factory=list)
    dependency_files: dict[str, str] = field(default_factory=dict)  # filename -> content
    config_files: dict[str, str] = field(default_factory=dict)
    dockerfile_content: str | None = None
    iac_files: dict[str, str] = field(default_factory=dict)

    # ── Knowledge Context ──────────────────────────────────────
    # Populated from Neo4j and Qdrant
    rag_context: str = ""
    graph_context: dict[str, Any] = field(default_factory=dict)
    known_vulnerabilities: list[dict] = field(default_factory=list)
    architecture_info: dict[str, Any] = field(default_factory=dict)

    # ── Agent Outputs ──────────────────────────────────────────
    # Each agent appends its findings/outputs here
    threat_model: dict[str, Any] = field(default_factory=dict)
    architecture_review: dict[str, Any] = field(default_factory=dict)

    # Findings from all agents (append-only)
    all_findings: list[dict] = field(default_factory=list)

    # Agent-specific results keyed by agent name
    agent_results: dict[str, dict] = field(default_factory=dict)

    # ── Patches & Tests ────────────────────────────────────────
    generated_patches: list[dict] = field(default_factory=list)
    generated_tests: list[dict] = field(default_factory=list)
    documentation_updates: list[dict] = field(default_factory=list)

    # ── Verification ───────────────────────────────────────────
    verification_passed: bool = False
    verification_results: dict[str, Any] = field(default_factory=dict)

    # ── Deployment Decision ────────────────────────────────────
    deployment_approved: bool = False
    deployment_decision: dict[str, Any] = field(default_factory=dict)
    security_score: int = 100
    overall_confidence: float = 0.0

    # ── PR Output ──────────────────────────────────────────────
    pr_url: str | None = None
    pr_body: str = ""
    pr_comments: list[dict] = field(default_factory=list)

    # ── Pipeline Control ───────────────────────────────────────
    current_phase: str = "queued"
    errors: list[str] = field(default_factory=list)
    agent_execution_order: list[str] = field(default_factory=list)

    # ── GitHub Event Context ───────────────────────────────────
    # Populated from webhook payload before pipeline starts
    event_type: str = "push"           # push, pull_request, deployment, etc.
    event_action: str | None = None    # opened, closed, created, etc.
    event_data: dict = field(default_factory=dict)    # raw extra event fields
    # Which agents the event router requests (empty = full pipeline)
    requested_agents: list[str] = field(default_factory=list)
    # True → run full 18-agent pipeline; False → graph-update-only or partial
    requires_full_pipeline: bool = True

    # ── Digital Twin Updates ───────────────────────────────────
    # Populated by the update_digital_twin node
    digital_twin_updates: list[dict] = field(default_factory=list)

    # ── Messages (for LangGraph message passing) ───────────────
    messages: Annotated[list, add_messages] = field(default_factory=list)

    def add_findings(self, agent_name: str, findings: list[dict]) -> None:
        """Add findings from an agent to the global list."""
        for f in findings:
            f["agent_name"] = agent_name
            self.all_findings.append(f)

    def get_severity_counts(self) -> dict[str, int]:
        """Count findings by severity."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in self.all_findings:
            sev = f.get("severity", "info").lower()
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def calculate_security_score(self) -> int:
        """Calculate security score (100 = perfect, 0 = critical risk)."""
        counts = self.get_severity_counts()
        deductions = (
            counts["critical"] * 25
            + counts["high"] * 10
            + counts["medium"] * 5
            + counts["low"] * 1
        )
        return max(0, 100 - deductions)
