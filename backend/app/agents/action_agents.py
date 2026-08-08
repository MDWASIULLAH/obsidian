"""
OBSIDIAN — Action Agents.

These agents take action based on findings from the security
scanning agents: simulate attacks, generate patches, generate
tests, update documentation, and approve deployments.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import AgentFinding, BaseAgent
from app.core import prompts


# ═══════════════════════════════════════════════════════════════════
# Attack Simulation Agent
# ═══════════════════════════════════════════════════════════════════


class AttackSimulationAgent(BaseAgent):
    name = "attack_simulation"
    purpose = "Simulate attack chains from identified vulnerabilities"
    reasoning_strategy = "tree_of_thought"
    model_tier = "reasoning"
    inputs = ["all_findings", "graph_context", "architecture_review"]
    outputs = ["findings", "attack_chains"]

    def get_system_prompt(self) -> str:
        return prompts.ATTACK_SIMULATION_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "attack_chains": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "steps": {"type": "array", "items": {"type": "object"}},
                            "probability": {"type": "number"},
                            "impact": {"type": "string"},
                            "mitre_techniques": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "risk_score": {"type": "integer"},
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        findings = context.get("all_findings", [])
        if not findings:
            return []

        findings_summary = json.dumps(findings[:30], indent=2, default=str)
        prompt = (
            f"## Attack Simulation\n\n"
            f"### Current Findings\n```json\n{findings_summary}\n```\n\n"
            f"Simulate how an attacker could chain these vulnerabilities. "
            f"Build attack trees with probability estimates."
        )

        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        context["attack_chains"] = result.get("attack_chains", [])

        attack_findings = []
        for chain in result.get("attack_chains", []):
            probability = chain.get("probability", 0.5)
            severity = "critical" if probability > 0.7 else "high" if probability > 0.4 else "medium"

            attack_findings.append(AgentFinding(
                title=f"Attack Chain: {chain.get('name', 'Unknown')}",
                description=chain.get("description", ""),
                severity=severity,
                category="vulnerability",
                confidence=probability,
                mitre_technique=", ".join(chain.get("mitre_techniques", [])),
                reasoning=json.dumps(chain.get("steps", []), default=str),
                recommendation=f"Impact: {chain.get('impact', 'Unknown')}",
            ))

        return attack_findings


# ═══════════════════════════════════════════════════════════════════
# Auto Patcher Agent
# ═══════════════════════════════════════════════════════════════════


class AutoPatcherAgent(BaseAgent):
    name = "auto_patcher"
    purpose = "Generate production-quality security patches"
    reasoning_strategy = "chain_of_thought"
    model_tier = "code"
    inputs = ["all_findings", "file_contents"]
    outputs = ["patches"]

    def get_system_prompt(self) -> str:
        return prompts.AUTO_PATCHER_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "patches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "finding_title": {"type": "string"},
                            "original_code": {"type": "string"},
                            "patched_code": {"type": "string"},
                            "diff": {"type": "string"},
                            "explanation": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                    },
                },
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        findings = context.get("all_findings", [])
        file_contents = context.get("file_contents", {})

        # Only patch critical and high severity findings
        patchable = [
            f for f in findings
            if f.get("severity") in ("critical", "high")
            and f.get("file_path")
            and f.get("file_path") in file_contents
        ]

        if not patchable:
            return []

        for finding in patchable[:10]:  # Limit to 10 patches per run
            file_path = finding["file_path"]
            file_code = file_contents.get(file_path, "")

            prompt = (
                f"## Generate Security Patch\n\n"
                f"### Vulnerability\n"
                f"Title: {finding.get('title')}\n"
                f"Description: {finding.get('description')}\n"
                f"Severity: {finding.get('severity')}\n"
                f"CWE: {finding.get('cwe_id', 'N/A')}\n\n"
                f"### Current Code ({file_path})\n```\n{file_code[:8000]}\n```\n\n"
                f"Generate a minimal, focused patch that fixes this vulnerability."
            )

            result = await self.reason_json(prompt)

            for patch in result.get("patches", []):
                context.setdefault("generated_patches", []).append({
                    "file_path": patch.get("file_path", file_path),
                    "finding_title": finding.get("title"),
                    "original_code": patch.get("original_code", ""),
                    "patched_code": patch.get("patched_code", ""),
                    "diff": patch.get("diff", ""),
                    "explanation": patch.get("explanation", ""),
                    "confidence": patch.get("confidence", 0.7),
                })

        return []  # Patches are stored in context, not as findings


# ═══════════════════════════════════════════════════════════════════
# Regression Test Agent
# ═══════════════════════════════════════════════════════════════════


class RegressionTestAgent(BaseAgent):
    name = "regression_tester"
    purpose = "Generate tests for security patches"
    reasoning_strategy = "chain_of_thought"
    model_tier = "code"
    inputs = ["generated_patches", "file_contents"]
    outputs = ["tests"]

    def get_system_prompt(self) -> str:
        return prompts.REGRESSION_TESTER_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tests": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "test_file": {"type": "string"},
                            "test_name": {"type": "string"},
                            "test_code": {"type": "string"},
                            "test_type": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                },
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        patches = context.get("generated_patches", [])
        if not patches:
            return []

        for patch in patches[:10]:
            prompt = (
                f"## Generate Security Tests\n\n"
                f"### Patch Details\n"
                f"File: {patch.get('file_path')}\n"
                f"Finding: {patch.get('finding_title')}\n"
                f"Explanation: {patch.get('explanation')}\n\n"
                f"### Patched Code\n```\n{patch.get('patched_code', '')[:5000]}\n```\n\n"
                f"Generate tests that verify the patch fixes the vulnerability."
            )

            result = await self.reason_json(prompt)

            for test in result.get("tests", []):
                context.setdefault("generated_tests", []).append({
                    "test_file": test.get("test_file", ""),
                    "test_name": test.get("test_name", ""),
                    "test_code": test.get("test_code", ""),
                    "test_type": test.get("test_type", "security"),
                    "description": test.get("description", ""),
                    "patch_file": patch.get("file_path"),
                })

        return []


# ═══════════════════════════════════════════════════════════════════
# Documentation Agent
# ═══════════════════════════════════════════════════════════════════


class DocumentationAgent(BaseAgent):
    name = "documentation"
    purpose = "Generate and update security documentation"
    reasoning_strategy = "chain_of_thought"
    model_tier = "code"
    inputs = ["all_findings", "generated_patches", "threat_model"]
    outputs = ["documentation"]

    def get_system_prompt(self) -> str:
        return prompts.DOCUMENTATION_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "type": {"type": "string"},
                        },
                    },
                },
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        findings = context.get("all_findings", [])
        patches = context.get("generated_patches", [])
        threat_model = context.get("threat_model", {})

        prompt = (
            f"## Security Documentation Update\n\n"
            f"### Findings Summary\n"
            f"Total: {len(findings)}\n"
            f"Critical: {sum(1 for f in findings if f.get('severity') == 'critical')}\n"
            f"High: {sum(1 for f in findings if f.get('severity') == 'high')}\n\n"
            f"### Patches Generated: {len(patches)}\n\n"
            f"### Threat Model Available: {'Yes' if threat_model else 'No'}\n\n"
            f"Generate SECURITY.md and CHANGELOG updates."
        )

        result = await self.reason_json(prompt)

        for doc in result.get("documents", []):
            context.setdefault("documentation_updates", []).append(doc)

        return []


# ═══════════════════════════════════════════════════════════════════
# Deployment Approval Agent
# ═══════════════════════════════════════════════════════════════════


class DeploymentApprovalAgent(BaseAgent):
    name = "deployment_approval"
    purpose = "Make GO/NO-GO deployment decisions"
    reasoning_strategy = "tree_of_thought"
    model_tier = "reasoning"
    inputs = ["all_findings", "generated_patches", "generated_tests", "security_score"]
    outputs = ["deployment_decision"]

    def get_system_prompt(self) -> str:
        return prompts.DEPLOYMENT_APPROVAL_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "approved": {"type": "boolean"},
                "confidence": {"type": "number"},
                "security_score": {"type": "integer"},
                "blocking_issues": {"type": "array", "items": {"type": "string"}},
                "conditions": {"type": "array", "items": {"type": "string"}},
                "rationale": {"type": "string"},
                "risk_acceptance": {"type": "string"},
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        findings = context.get("all_findings", [])
        patches = context.get("generated_patches", [])
        tests = context.get("generated_tests", [])

        severity_counts = {}
        for f in findings:
            sev = f.get("severity", "info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        prompt = (
            f"## Deployment Approval Decision\n\n"
            f"### Security Summary\n"
            f"- Total Findings: {len(findings)}\n"
            f"- Severity: {json.dumps(severity_counts)}\n"
            f"- Patches Generated: {len(patches)}\n"
            f"- Tests Generated: {len(tests)}\n\n"
            f"### Unpatched Critical/High\n"
            f"- Critical: {severity_counts.get('critical', 0)}\n"
            f"- High: {severity_counts.get('high', 0)}\n\n"
            f"Make a GO/NO-GO decision."
        )

        result = await self.reason_json(prompt)

        context["deployment_decision"] = result
        context["deployment_approved"] = result.get("approved", False)
        context["overall_confidence"] = result.get("confidence", 0.0)
        context["security_score"] = result.get("security_score", 0)

        return []


# ═══════════════════════════════════════════════════════════════════
# Learning Agent
# ═══════════════════════════════════════════════════════════════════


class LearningAgent(BaseAgent):
    name = "learning_agent"
    purpose = "Learn from pipeline outcomes to improve future runs"
    reasoning_strategy = "chain_of_thought"
    model_tier = "reasoning"
    inputs = ["all_findings", "generated_patches", "deployment_decision"]
    outputs = ["learned_patterns"]

    def get_system_prompt(self) -> str:
        return prompts.LEARNING_AGENT_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "patterns": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}},
                "false_positive_indicators": {"type": "array", "items": {"type": "string"}},
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        findings = context.get("all_findings", [])
        decision = context.get("deployment_decision", {})

        prompt = (
            f"## Learning Analysis\n\n"
            f"Findings: {len(findings)}\n"
            f"Deployment: {'Approved' if decision.get('approved') else 'Blocked'}\n\n"
            f"Identify patterns, false positive indicators, and pipeline improvements."
        )

        result = await self.reason_json(prompt)

        # Store learned patterns for future runs
        for pattern in result.get("patterns", []):
            self.memory.add_pattern(pattern)

        return []
