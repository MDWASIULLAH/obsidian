"""
OBSIDIAN — Threat Modeling Agent.

Performs STRIDE/DREAD threat analysis on code changes,
generates attack trees, and maps to MITRE ATT&CK.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentFinding, BaseAgent
from app.core.prompts import THREAT_MODELER_SYSTEM, CODE_DIFF_TEMPLATE


class ThreatModelingAgent(BaseAgent):
    name = "threat_modeler"
    purpose = "Perform STRIDE/DREAD threat modeling on code changes"
    reasoning_strategy = "tree_of_thought"
    model_tier = "reasoning"
    inputs = ["code_diff", "architecture_info", "rag_context"]
    outputs = ["findings", "threat_model"]

    def get_system_prompt(self) -> str:
        return THREAT_MODELER_SYSTEM

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "threats": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "stride_category": {"type": "string", "enum": [
                                "Spoofing", "Tampering", "Repudiation",
                                "Information Disclosure", "Denial of Service",
                                "Elevation of Privilege"
                            ]},
                            "description": {"type": "string"},
                            "severity": {"type": "string"},
                            "dread_score": {
                                "type": "object",
                                "properties": {
                                    "damage": {"type": "integer", "minimum": 1, "maximum": 10},
                                    "reproducibility": {"type": "integer"},
                                    "exploitability": {"type": "integer"},
                                    "affected_users": {"type": "integer"},
                                    "discoverability": {"type": "integer"},
                                },
                            },
                            "mitre_technique": {"type": "string"},
                            "cwe_id": {"type": "string"},
                            "attack_vector": {"type": "string"},
                            "affected_component": {"type": "string"},
                            "mitigation": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                    },
                },
                "attack_tree": {"type": "object"},
                "trust_boundaries": {"type": "array", "items": {"type": "string"}},
                "data_flows": {"type": "array", "items": {"type": "string"}},
            },
        }

    async def analyze(self, context: dict[str, Any]) -> list[AgentFinding]:
        diff = context.get("diff_content", "")
        files = context.get("changed_files", [])
        rag = context.get("rag_context", "")

        if not diff and not files:
            return []

        prompt = CODE_DIFF_TEMPLATE.format(
            repository=context.get("repository_full_name", "unknown"),
            branch=context.get("branch", "main"),
            commit_sha=context.get("commit_sha", "unknown"),
            changed_files="\n".join(f"- {f}" for f in files),
            diff_content=diff[:12000],  # Limit diff size for context window
        )

        result = await self.reason_json(prompt, rag_context=rag)

        findings = []
        for threat in result.get("threats", []):
            dread = threat.get("dread_score", {})
            dread_total = sum(dread.values()) if dread else 0
            dread_avg = dread_total / max(len(dread), 1)

            # Map DREAD score to severity
            if dread_avg >= 8:
                severity = "critical"
            elif dread_avg >= 6:
                severity = "high"
            elif dread_avg >= 4:
                severity = "medium"
            else:
                severity = "low"

            findings.append(AgentFinding(
                title=threat.get("title", "Unknown Threat"),
                description=threat.get("description", ""),
                severity=threat.get("severity", severity),
                category="vulnerability",
                confidence=threat.get("confidence", 0.7),
                cwe_id=threat.get("cwe_id"),
                owasp_category=threat.get("stride_category"),
                mitre_technique=threat.get("mitre_technique"),
                recommendation=threat.get("mitigation"),
                reasoning=f"STRIDE: {threat.get('stride_category')} | DREAD: {dread_avg:.1f}",
            ))

        # Store the full threat model in context for downstream agents
        context["threat_model"] = result

        return findings
