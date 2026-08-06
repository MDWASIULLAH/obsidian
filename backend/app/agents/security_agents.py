"""
SENTINEL AI X — Remaining Specialized Security Agents.

Each agent follows the BaseAgent contract with specific
system prompts, output schemas, and analysis logic.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentFinding, BaseAgent
from app.core import prompts


# ═══════════════════════════════════════════════════════════════════
# Architecture Review Agent
# ═══════════════════════════════════════════════════════════════════


class ArchitectureReviewAgent(BaseAgent):
    name = "architecture_reviewer"
    purpose = "Review system architecture for security design flaws"
    reasoning_strategy = "tree_of_thought"
    model_tier = "reasoning"
    inputs = ["file_contents", "config_files", "graph_context"]
    outputs = ["findings", "architecture_review"]

    def get_system_prompt(self) -> str:
        return prompts.ARCHITECTURE_REVIEWER_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "design_issues": {"type": "array", "items": {"type": "object"}},
                "trust_boundaries": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}},
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        files = context.get("file_contents", {})
        configs = context.get("config_files", {})
        if not files and not configs:
            return []

        content_summary = "\n".join(
            f"- {name} ({len(content)} chars)"
            for name, content in list(files.items())[:30]
        )
        config_content = "\n".join(
            f"### {name}\n```\n{content[:2000]}\n```"
            for name, content in list(configs.items())[:10]
        )

        prompt = (
            f"## Repository Architecture Analysis\n\n"
            f"### Files in Repository\n{content_summary}\n\n"
            f"### Configuration Files\n{config_content}\n\n"
            f"Analyze the architecture for security design flaws."
        )

        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        findings = []
        for issue in result.get("design_issues", []):
            findings.append(AgentFinding(
                title=issue.get("title", "Architecture Issue"),
                description=issue.get("description", ""),
                severity=issue.get("severity", "medium"),
                category="design_flaw",
                confidence=issue.get("confidence", 0.6),
                recommendation=issue.get("recommendation"),
            ))
        context["architecture_review"] = result
        return findings


# ═══════════════════════════════════════════════════════════════════
# Dependency Intelligence Agent
# ═══════════════════════════════════════════════════════════════════


class DependencyIntelAgent(BaseAgent):
    name = "dependency_intel"
    purpose = "Analyze dependencies for CVEs, license issues, and supply chain risks"
    reasoning_strategy = "chain_of_thought"
    model_tier = "lightweight"
    inputs = ["dependency_files"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return prompts.DEPENDENCY_INTEL_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "vulnerabilities": {"type": "array", "items": {"type": "object"}},
                "license_issues": {"type": "array", "items": {"type": "object"}},
                "outdated": {"type": "array", "items": {"type": "object"}},
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        dep_files = context.get("dependency_files", {})
        if not dep_files:
            return []

        dep_content = "\n".join(
            f"### {name}\n```\n{content[:4000]}\n```"
            for name, content in dep_files.items()
        )
        prompt = f"## Dependency Analysis\n\n{dep_content}\n\nAnalyze for CVEs, license issues, and supply chain risks."

        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        findings = []
        for vuln in result.get("vulnerabilities", []):
            findings.append(AgentFinding(
                title=vuln.get("title", "Dependency Vulnerability"),
                description=vuln.get("description", ""),
                severity=vuln.get("severity", "high"),
                category="dependency",
                confidence=vuln.get("confidence", 0.8),
                cve_id=vuln.get("cve_id"),
                recommendation=vuln.get("recommendation"),
            ))
        for issue in result.get("license_issues", []):
            findings.append(AgentFinding(
                title=issue.get("title", "License Issue"),
                description=issue.get("description", ""),
                severity="medium",
                category="license",
                confidence=0.9,
                recommendation=issue.get("recommendation"),
            ))
        return findings


# ═══════════════════════════════════════════════════════════════════
# Secrets Detection Agent
# ═══════════════════════════════════════════════════════════════════


class SecretsDetectionAgent(BaseAgent):
    name = "secrets_detection"
    purpose = "Detect hardcoded secrets, API keys, and credentials"
    reasoning_strategy = "chain_of_thought"
    model_tier = "lightweight"
    inputs = ["code_diff", "file_contents"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return prompts.SECRETS_DETECTION_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "secrets": {"type": "array", "items": {"type": "object"}},
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        diff = context.get("diff_content", "")
        if not diff:
            return []

        prompt = f"## Secrets Detection Scan\n\n```diff\n{diff[:12000]}\n```\n\nScan for hardcoded secrets. REDACT actual values."

        result = await self.reason_json(prompt)
        findings = []
        for secret in result.get("secrets", []):
            findings.append(AgentFinding(
                title=secret.get("title", "Hardcoded Secret"),
                description=secret.get("description", ""),
                severity="critical",
                category="secret",
                confidence=secret.get("confidence", 0.9),
                file_path=secret.get("file_path"),
                line_start=secret.get("line_number"),
                recommendation=secret.get("recommendation", "Move to environment variables or a secrets vault"),
            ))
        return findings


# ═══════════════════════════════════════════════════════════════════
# Infrastructure Security Agent
# ═══════════════════════════════════════════════════════════════════


class InfraSecurityAgent(BaseAgent):
    name = "infra_security"
    purpose = "Analyze IaC for misconfigurations"
    reasoning_strategy = "chain_of_thought"
    model_tier = "code"
    inputs = ["iac_files", "config_files"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return prompts.INFRA_SECURITY_SYSTEM

    def get_output_schema(self) -> dict:
        return {"type": "object", "properties": {"misconfigurations": {"type": "array", "items": {"type": "object"}}}}

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        iac = context.get("iac_files", {})
        configs = context.get("config_files", {})
        combined = {**iac, **configs}
        if not combined:
            return []

        content = "\n".join(f"### {n}\n```\n{c[:3000]}\n```" for n, c in list(combined.items())[:10])
        prompt = f"## Infrastructure Security Analysis\n\n{content}"

        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        return [
            AgentFinding(
                title=m.get("title", "IaC Misconfiguration"),
                description=m.get("description", ""),
                severity=m.get("severity", "high"),
                category="misconfiguration",
                confidence=m.get("confidence", 0.7),
                file_path=m.get("file_path"),
                recommendation=m.get("recommendation"),
                cwe_id=m.get("cwe_id"),
            )
            for m in result.get("misconfigurations", [])
        ]


# ═══════════════════════════════════════════════════════════════════
# Container Security Agent
# ═══════════════════════════════════════════════════════════════════


class ContainerSecurityAgent(BaseAgent):
    name = "container_security"
    purpose = "Analyze Dockerfiles and container configurations"
    reasoning_strategy = "chain_of_thought"
    model_tier = "code"
    inputs = ["dockerfile_content", "config_files"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return prompts.CONTAINER_SECURITY_SYSTEM

    def get_output_schema(self) -> dict:
        return {"type": "object", "properties": {"issues": {"type": "array", "items": {"type": "object"}}}}

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        dockerfile = context.get("dockerfile_content", "")
        if not dockerfile:
            return []

        prompt = f"## Dockerfile Analysis\n\n```dockerfile\n{dockerfile[:5000]}\n```"
        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        return [
            AgentFinding(
                title=i.get("title", "Container Issue"),
                description=i.get("description", ""),
                severity=i.get("severity", "medium"),
                category="misconfiguration",
                confidence=i.get("confidence", 0.7),
                recommendation=i.get("recommendation"),
            )
            for i in result.get("issues", [])
        ]


# ═══════════════════════════════════════════════════════════════════
# Cloud Security Agent
# ═══════════════════════════════════════════════════════════════════


class CloudSecurityAgent(BaseAgent):
    name = "cloud_security"
    purpose = "Detect cloud misconfigurations across AWS/GCP/Azure"
    reasoning_strategy = "chain_of_thought"
    model_tier = "code"
    inputs = ["iac_files", "config_files"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return prompts.CLOUD_SECURITY_SYSTEM

    def get_output_schema(self) -> dict:
        return {"type": "object", "properties": {"misconfigurations": {"type": "array", "items": {"type": "object"}}}}

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        iac = context.get("iac_files", {})
        configs = context.get("config_files", {})
        combined = {**iac, **configs}
        if not combined:
            return []

        content = "\n".join(f"### {n}\n```\n{c[:3000]}\n```" for n, c in list(combined.items())[:10])
        prompt = f"## Cloud Security Analysis\n\n{content}"

        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        return [
            AgentFinding(
                title=m.get("title", "Cloud Misconfiguration"),
                description=m.get("description", ""),
                severity=m.get("severity", "high"),
                category="misconfiguration",
                confidence=m.get("confidence", 0.7),
                file_path=m.get("file_path"),
                recommendation=m.get("recommendation"),
            )
            for m in result.get("misconfigurations", [])
        ]


# ═══════════════════════════════════════════════════════════════════
# API Security Agent
# ═══════════════════════════════════════════════════════════════════


class APISecurityAgent(BaseAgent):
    name = "api_security"
    purpose = "Analyze API endpoints for security vulnerabilities"
    reasoning_strategy = "chain_of_thought"
    model_tier = "code"
    inputs = ["code_diff", "file_contents", "config_files"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return prompts.API_SECURITY_SYSTEM

    def get_output_schema(self) -> dict:
        return {"type": "object", "properties": {"api_issues": {"type": "array", "items": {"type": "object"}}}}

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        diff = context.get("diff_content", "")
        files = context.get("file_contents", {})
        if not diff and not files:
            return []

        api_files = {k: v for k, v in files.items() if any(
            kw in k.lower() for kw in ["route", "api", "endpoint", "controller", "view", "handler"]
        )}

        content = "\n".join(f"### {n}\n```\n{c[:3000]}\n```" for n, c in list(api_files.items())[:8])
        prompt = f"## API Security Analysis\n\nDiff:\n```diff\n{diff[:6000]}\n```\n\nAPI Files:\n{content}"

        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        return [
            AgentFinding(
                title=i.get("title", "API Vulnerability"),
                description=i.get("description", ""),
                severity=i.get("severity", "high"),
                category="vulnerability",
                confidence=i.get("confidence", 0.7),
                file_path=i.get("file_path"),
                line_start=i.get("line_start"),
                cwe_id=i.get("cwe_id"),
                owasp_category=i.get("owasp_category"),
                recommendation=i.get("recommendation"),
            )
            for i in result.get("api_issues", [])
        ]


# ═══════════════════════════════════════════════════════════════════
# Business Logic Agent
# ═══════════════════════════════════════════════════════════════════


class BusinessLogicAgent(BaseAgent):
    name = "business_logic"
    purpose = "Detect business logic flaws and authorization bypasses"
    reasoning_strategy = "tree_of_thought"
    model_tier = "reasoning"
    inputs = ["code_diff", "file_contents"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return prompts.BUSINESS_LOGIC_SYSTEM

    def get_output_schema(self) -> dict:
        return {"type": "object", "properties": {"logic_flaws": {"type": "array", "items": {"type": "object"}}}}

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        diff = context.get("diff_content", "")
        if not diff:
            return []

        prompt = f"## Business Logic Analysis\n\n```diff\n{diff[:12000]}\n```\n\nIdentify logic flaws, race conditions, and auth bypasses."
        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        return [
            AgentFinding(
                title=f.get("title", "Logic Flaw"),
                description=f.get("description", ""),
                severity=f.get("severity", "high"),
                category="logic_error",
                confidence=f.get("confidence", 0.6),
                file_path=f.get("file_path"),
                recommendation=f.get("recommendation"),
            )
            for f in result.get("logic_flaws", [])
        ]


# ═══════════════════════════════════════════════════════════════════
# LLM Security Agent
# ═══════════════════════════════════════════════════════════════════


class LLMSecurityAgent(BaseAgent):
    name = "llm_security"
    purpose = "Detect prompt injection, RAG poisoning, and LLM vulnerabilities"
    reasoning_strategy = "tree_of_thought"
    model_tier = "reasoning"
    inputs = ["code_diff", "file_contents"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return prompts.LLM_SECURITY_SYSTEM

    def get_output_schema(self) -> dict:
        return {"type": "object", "properties": {"llm_issues": {"type": "array", "items": {"type": "object"}}}}

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        diff = context.get("diff_content", "")
        files = context.get("file_contents", {})

        # Only analyze if LLM-related code is present
        llm_keywords = ["openai", "langchain", "llm", "prompt", "embedding", "rag", "chat", "completion"]
        has_llm_code = any(
            any(kw in content.lower() for kw in llm_keywords)
            for content in list(files.values())[:20]
        )
        if not has_llm_code and not any(kw in diff.lower() for kw in llm_keywords):
            return []

        prompt = f"## LLM Security Analysis\n\n```diff\n{diff[:12000]}\n```"
        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        return [
            AgentFinding(
                title=i.get("title", "LLM Vulnerability"),
                description=i.get("description", ""),
                severity=i.get("severity", "high"),
                category="prompt_injection",
                confidence=i.get("confidence", 0.7),
                file_path=i.get("file_path"),
                recommendation=i.get("recommendation"),
            )
            for i in result.get("llm_issues", [])
        ]


# ═══════════════════════════════════════════════════════════════════
# Compliance Agent
# ═══════════════════════════════════════════════════════════════════


class ComplianceAgent(BaseAgent):
    name = "compliance"
    purpose = "Map code to compliance frameworks (GDPR, SOC2, HIPAA, PCI-DSS)"
    reasoning_strategy = "chain_of_thought"
    model_tier = "lightweight"
    inputs = ["code_diff", "file_contents", "config_files"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return prompts.COMPLIANCE_SYSTEM

    def get_output_schema(self) -> dict:
        return {"type": "object", "properties": {"compliance_gaps": {"type": "array", "items": {"type": "object"}}}}

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        diff = context.get("diff_content", "")
        if not diff:
            return []

        prompt = f"## Compliance Analysis\n\n```diff\n{diff[:10000]}\n```\n\nCheck for GDPR, SOC2, HIPAA, PCI-DSS gaps."
        result = await self.reason_json(prompt, rag_context=context.get("rag_context", ""))
        return [
            AgentFinding(
                title=g.get("title", "Compliance Gap"),
                description=g.get("description", ""),
                severity=g.get("severity", "medium"),
                category="compliance",
                confidence=g.get("confidence", 0.6),
                recommendation=g.get("recommendation"),
            )
            for g in result.get("compliance_gaps", [])
        ]
