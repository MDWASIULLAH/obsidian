"""
OBSIDIAN — Base Agent Abstract Class.

Every specialized agent inherits from this class. It provides:
  - Unified interface for execution
  - Model routing integration
  - RAG context enrichment
  - Knowledge Graph querying
  - Confidence scoring
  - Memory persistence
  - Failure recovery with retries
  - Metrics collection
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.model_router import ModelResponse, get_model_router
from app.core.prompts import (
    RAG_CONTEXT_TEMPLATE,
    STRUCTURED_OUTPUT_INSTRUCTION,
)

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════


@dataclass
class AgentFinding:
    """A single security finding produced by an agent."""
    title: str
    description: str
    severity: str  # critical, high, medium, low, info
    category: str
    confidence: float  # 0.0 - 1.0
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    cwe_id: str | None = None
    cve_id: str | None = None
    owasp_category: str | None = None
    mitre_technique: str | None = None
    recommendation: str | None = None
    reasoning: str | None = None
    citations: list[str] = field(default_factory=list)


@dataclass
class AgentOutput:
    """Structured output from an agent execution."""
    agent_name: str
    status: str  # completed, failed, skipped
    findings: list[AgentFinding] = field(default_factory=list)
    patches: list[dict] = field(default_factory=list)
    tests: list[dict] = field(default_factory=list)
    documentation: list[dict] = field(default_factory=list)
    confidence_score: float = 0.0
    reasoning_trace: str = ""
    summary: str = ""
    raw_output: str = ""
    model_used: str = ""
    tokens_used: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_findings: int = 0
    total_tokens: int = 0
    avg_confidence: float = 0.0
    avg_duration_ms: float = 0.0


@dataclass
class AgentMemory:
    """
    Persistent memory for an agent across runs.

    Stores previous findings, learned patterns, and developer
    preferences to improve accuracy over time.
    """
    previous_findings: list[dict] = field(default_factory=list)
    learned_patterns: list[str] = field(default_factory=list)
    false_positives: list[dict] = field(default_factory=list)
    repository_context: dict = field(default_factory=dict)

    def add_finding(self, finding: dict) -> None:
        self.previous_findings.append(finding)
        # Keep only last 100 findings in memory
        if len(self.previous_findings) > 100:
            self.previous_findings = self.previous_findings[-100:]

    def add_pattern(self, pattern: str) -> None:
        if pattern not in self.learned_patterns:
            self.learned_patterns.append(pattern)

    def mark_false_positive(self, finding: dict) -> None:
        self.false_positives.append(finding)


# ═══════════════════════════════════════════════════════════════════
# Base Agent
# ═══════════════════════════════════════════════════════════════════


class BaseAgent(ABC):
    """
    Abstract base class for all OBSIDIAN agents.

    Subclasses must implement:
      - name, purpose, reasoning_strategy, model_tier
      - analyze(): The core analysis logic
      - get_output_schema(): JSON schema for structured output
    """

    # ── Identity (override in subclasses) ──────────────────────
    name: str = "base_agent"
    purpose: str = "Base security agent"
    reasoning_strategy: str = "chain_of_thought"  # chain_of_thought | tree_of_thought | react
    model_tier: str = "reasoning"  # reasoning | code | lightweight
    inputs: list[str] = ["code_diff", "repository_context"]
    outputs: list[str] = ["findings"]

    def __init__(self) -> None:
        self.router = get_model_router()
        self.metrics = AgentMetrics()
        self.memory = AgentMemory()
        self._logger = logger.bind(agent=self.name)

    # ── Abstract Methods ───────────────────────────────────────

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the agent's system prompt."""

    @abstractmethod
    def get_output_schema(self) -> dict:
        """Return JSON schema for the agent's structured output."""

    @abstractmethod
    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        """
        Core analysis logic. Receives context and returns findings.

        Args:
            context: Dict with keys like 'diff', 'files', 'repo_info',
                     'rag_context', 'graph_context', etc.

        Returns:
            List of AgentFinding objects
        """

    # ── Main Execution Entry Point ─────────────────────────────

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        """
        Execute the agent with full lifecycle management.

        This handles: timing, error recovery, metrics, memory.
        """
        start = time.perf_counter()
        self._logger.info("Agent execution started")

        try:
            # Run the analysis
            findings = await self.analyze(context)

            duration = (time.perf_counter() - start) * 1000

            # Calculate confidence
            if findings:
                avg_confidence = sum(f.confidence for f in findings) / len(findings)
            else:
                avg_confidence = 1.0  # No findings = high confidence in clean code

            output = AgentOutput(
                agent_name=self.name,
                status="completed",
                findings=findings,
                confidence_score=avg_confidence,
                summary=f"Found {len(findings)} issue(s)",
                duration_ms=duration,
            )

            # Update metrics
            self.metrics.total_runs += 1
            self.metrics.successful_runs += 1
            self.metrics.total_findings += len(findings)

            # Update memory
            for f in findings:
                self.memory.add_finding({
                    "title": f.title,
                    "severity": f.severity,
                    "cwe_id": f.cwe_id,
                })

            self._logger.info(
                "Agent execution completed",
                findings=len(findings),
                confidence=f"{avg_confidence:.2f}",
                duration_ms=f"{duration:.0f}",
            )

            return output

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._logger.error("Agent execution failed", error=str(e))

            self.metrics.total_runs += 1
            self.metrics.failed_runs += 1

            # Attempt recovery
            try:
                return await self.recover(e, context)
            except Exception:
                return AgentOutput(
                    agent_name=self.name,
                    status="failed",
                    error=str(e),
                    duration_ms=duration,
                )

    # ── LLM Interaction Helpers ────────────────────────────────

    async def reason(
        self,
        user_prompt: str,
        rag_context: str = "",
        additional_system: str = "",
    ) -> ModelResponse:
        """
        Send a reasoning request to the model with full context.

        Automatically injects:
          - System prompt
          - RAG context
          - Structured output instructions
        """
        messages = [
            {"role": "system", "content": self._build_system_message(rag_context, additional_system)},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            tier=self.model_tier,
            messages=messages,
        )

        return response

    async def reason_json(
        self,
        user_prompt: str,
        rag_context: str = "",
        additional_system: str = "",
    ) -> dict:
        """Send a reasoning request and parse JSON output."""
        messages = [
            {"role": "system", "content": self._build_system_message(rag_context, additional_system)},
            {"role": "user", "content": user_prompt},
        ]

        return await self.router.complete_json(
            tier=self.model_tier,
            messages=messages,
        )

    def _build_system_message(self, rag_context: str, additional: str) -> str:
        """Construct the full system message with all context."""
        parts = [self.get_system_prompt()]

        if rag_context:
            parts.append(RAG_CONTEXT_TEMPLATE.format(rag_context=rag_context))

        if self.memory.learned_patterns:
            patterns = "\n".join(f"- {p}" for p in self.memory.learned_patterns[-10:])
            parts.append(f"\n## Learned Patterns\n{patterns}")

        parts.append(STRUCTURED_OUTPUT_INSTRUCTION.format(
            output_schema=json.dumps(self.get_output_schema(), indent=2)
        ))

        if additional:
            parts.append(additional)

        return "\n\n".join(parts)

    # ── Recovery ───────────────────────────────────────────────

    async def recover(self, error: Exception, context: dict[str, Any]) -> AgentOutput:
        """
        Attempt to recover from a failure.

        Default: Try with a simpler model tier. Override for custom recovery.
        """
        self._logger.warning("Attempting recovery", error=str(error))

        # Fallback to lightweight tier for a simpler analysis
        original_tier = self.model_tier
        self.model_tier = "lightweight"

        try:
            findings = await self.analyze(context)
            return AgentOutput(
                agent_name=self.name,
                status="completed",
                findings=findings,
                confidence_score=0.5,  # Lower confidence for recovery
                summary=f"Recovered: {len(findings)} findings (reduced accuracy)",
                metadata={"recovered": True, "original_error": str(error)},
            )
        finally:
            self.model_tier = original_tier

    # ── Info ───────────────────────────────────────────────────

    def get_info(self) -> dict:
        """Return agent metadata for the registry."""
        return {
            "name": self.name,
            "purpose": self.purpose,
            "model_tier": self.model_tier,
            "reasoning_strategy": self.reasoning_strategy,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metrics": {
                "total_runs": self.metrics.total_runs,
                "success_rate": (
                    self.metrics.successful_runs / max(self.metrics.total_runs, 1)
                ),
                "total_findings": self.metrics.total_findings,
            },
        }
