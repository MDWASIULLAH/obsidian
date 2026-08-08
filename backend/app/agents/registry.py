"""
OBSIDIAN — Agent Registry & Factory.

Central registry of all available agents. The orchestrator uses
this to instantiate and manage agents dynamically.
"""

from __future__ import annotations

from typing import Type

from app.agents.base import BaseAgent
from app.agents.threat_modeler import ThreatModelingAgent
from app.agents.code_intelligence import CodeIntelligenceAgent
from app.agents.threat_evolution_agent import ThreatEvolutionAgent
from app.agents.security_agents import (
    ArchitectureReviewAgent,
    DependencyIntelAgent,
    SecretsDetectionAgent,
    InfraSecurityAgent,
    ContainerSecurityAgent,
    CloudSecurityAgent,
    APISecurityAgent,
    BusinessLogicAgent,
    LLMSecurityAgent,
    ComplianceAgent,
)
from app.agents.action_agents import (
    AttackSimulationAgent,
    AutoPatcherAgent,
    RegressionTestAgent,
    DocumentationAgent,
    DeploymentApprovalAgent,
    LearningAgent,
)


# ═══════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════

# Ordered mapping — insertion order determines default execution order
AGENT_CLASSES: dict[str, Type[BaseAgent]] = {
    # Security Scanning Agents (run in parallel)
    "threat_modeler": ThreatModelingAgent,
    "architecture_reviewer": ArchitectureReviewAgent,
    "code_intelligence": CodeIntelligenceAgent,
    "dependency_intel": DependencyIntelAgent,
    "secrets_detection": SecretsDetectionAgent,
    "infra_security": InfraSecurityAgent,
    "container_security": ContainerSecurityAgent,
    "cloud_security": CloudSecurityAgent,
    "api_security": APISecurityAgent,
    "business_logic": BusinessLogicAgent,
    "llm_security": LLMSecurityAgent,
    "compliance": ComplianceAgent,
    "threat_evolution": ThreatEvolutionAgent,
    # Action Agents (run sequentially after scanning)
    "attack_simulation": AttackSimulationAgent,
    "auto_patcher": AutoPatcherAgent,
    "regression_tester": RegressionTestAgent,
    "documentation": DocumentationAgent,
    "deployment_approval": DeploymentApprovalAgent,
    "learning_agent": LearningAgent,
}

# Agents that scan in parallel
PARALLEL_SCAN_AGENTS = [
    "threat_modeler",
    "architecture_reviewer",
    "code_intelligence",
    "dependency_intel",
    "secrets_detection",
    "infra_security",
    "container_security",
    "cloud_security",
    "api_security",
    "business_logic",
    "llm_security",
    "compliance",
    "threat_evolution",
]

# Agents that run sequentially after scanning
SEQUENTIAL_ACTION_AGENTS = [
    "attack_simulation",
    "auto_patcher",
    "regression_tester",
    "documentation",
    "deployment_approval",
    "learning_agent",
]


class AgentRegistry:
    """
    Factory and registry for all security agents.

    Manages agent lifecycle: instantiation, caching, and metadata.
    """

    def __init__(self) -> None:
        self._instances: dict[str, BaseAgent] = {}

    def get_agent(self, name: str) -> BaseAgent:
        """Get or create an agent by name (cached)."""
        if name not in self._instances:
            cls = AGENT_CLASSES.get(name)
            if cls is None:
                raise ValueError(
                    f"Unknown agent: {name!r}. "
                    f"Available: {list(AGENT_CLASSES.keys())}"
                )
            self._instances[name] = cls()
        return self._instances[name]

    def get_all_agents(self) -> list[BaseAgent]:
        """Instantiate and return all registered agents."""
        return [self.get_agent(name) for name in AGENT_CLASSES]

    def get_scan_agents(self) -> list[BaseAgent]:
        """Return agents that run during parallel scan phase."""
        return [self.get_agent(name) for name in PARALLEL_SCAN_AGENTS]

    def get_action_agents(self) -> list[BaseAgent]:
        """Return agents that run sequentially after scanning."""
        return [self.get_agent(name) for name in SEQUENTIAL_ACTION_AGENTS]

    def list_agents(self) -> list[dict]:
        """Return metadata for all registered agents."""
        return [self.get_agent(name).get_info() for name in AGENT_CLASSES]

    def get_agent_names(self) -> list[str]:
        """Return all registered agent names."""
        return list(AGENT_CLASSES.keys())


# ── Singleton ──────────────────────────────────────────────────────

_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Get or create the singleton AgentRegistry."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
