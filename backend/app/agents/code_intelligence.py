"""
OBSIDIAN — Code Intelligence Agent.

Deep static analysis on code changes to detect injection
vulnerabilities, auth bypasses, data flow issues, and more.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentFinding, BaseAgent
from app.core.prompts import CODE_INTELLIGENCE_SYSTEM, CODE_DIFF_TEMPLATE


class CodeIntelligenceAgent(BaseAgent):
    name = "code_intelligence"
    purpose = "Deep code security analysis for vulnerabilities"
    reasoning_strategy = "chain_of_thought"
    model_tier = "code"
    inputs = ["code_diff", "file_contents", "rag_context"]
    outputs = ["findings"]

    def get_system_prompt(self) -> str:
        return CODE_INTELLIGENCE_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "vulnerabilities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "severity": {"type": "string"},
                            "vulnerability_type": {"type": "string"},
                            "cwe_id": {"type": "string"},
                            "owasp_category": {"type": "string"},
                            "file_path": {"type": "string"},
                            "line_start": {"type": "integer"},
                            "line_end": {"type": "integer"},
                            "code_snippet": {"type": "string"},
                            "attack_scenario": {"type": "string"},
                            "recommendation": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                    },
                },
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        diff = context.get("diff_content", "")
        files = context.get("changed_files", [])
        file_contents = context.get("file_contents", {})
        rag = context.get("rag_context", "")

        if not diff:
            return []

        # Build detailed code context
        code_context = ""
        for fname, content in list(file_contents.items())[:10]:
            code_context += f"\n### {fname}\n```\n{content[:3000]}\n```\n"

        prompt = CODE_DIFF_TEMPLATE.format(
            repository=context.get("repository_full_name", "unknown"),
            branch=context.get("branch", "main"),
            commit_sha=context.get("commit_sha", "unknown"),
            changed_files="\n".join(f"- {f}" for f in files),
            diff_content=diff[:12000],
        )

        if code_context:
            prompt += f"\n\n## Full File Contents\n{code_context}"

        result = await self.reason_json(prompt, rag_context=rag)

        findings = []
        for vuln in result.get("vulnerabilities", []):
            findings.append(AgentFinding(
                title=vuln.get("title", "Code Vulnerability"),
                description=vuln.get("description", ""),
                severity=vuln.get("severity", "medium"),
                category="vulnerability",
                confidence=vuln.get("confidence", 0.7),
                file_path=vuln.get("file_path"),
                line_start=vuln.get("line_start"),
                line_end=vuln.get("line_end"),
                code_snippet=vuln.get("code_snippet"),
                cwe_id=vuln.get("cwe_id"),
                owasp_category=vuln.get("owasp_category"),
                recommendation=vuln.get("recommendation"),
                reasoning=vuln.get("attack_scenario"),
            ))

        return findings
