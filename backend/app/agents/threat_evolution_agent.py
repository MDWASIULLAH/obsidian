"""
SENTINEL AI X — Threat Evolution Agent.

Uses NVIDIA NIM (reasoning tier) to:
  1. Analyse historical threat snapshots for a repository
  2. Predict how each threat will evolve over the next 30/60/90 days
  3. Identify which vulnerabilities are likely to be weaponised
  4. Generate MITRE ATT&CK kill-chain progression forecasts
  5. Produce prioritised remediation timelines

Output is stored in Neo4j (PredictedTrajectory nodes) and returned
as AgentOutput findings with trajectory metadata.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.agents.base import AgentFinding, AgentOutput, BaseAgent
from app.config import get_settings

logger = structlog.get_logger()

_SYSTEM_PROMPT = """
You are the SENTINEL AI X Threat Evolution Analyst — a Distinguished Security Researcher
specialising in predictive vulnerability intelligence.

Your role is to analyse the historical evolution of security threats in a software repository
and predict their future trajectories with high precision.

For each threat you will:
1. Assess current severity, velocity (rate of change), and exploitability
2. Map to MITRE ATT&CK tactics and predict likely next techniques
3. Estimate weaponisation probability (0-1) within 30, 60, and 90 days
4. Predict peak risk date and severity at peak
5. Recommend remediation deadline based on trajectory

Always output ONLY valid JSON matching the schema provided.
""".strip()

_ANALYSIS_PROMPT = """
Repository: {repo}
Analysis Date: {date}

## Current Threat Landscape

{threat_summary}

## Historical Evolution Data

{evolution_data}

## Known CVE Context

{cve_context}

## Task

For each threat listed, predict its evolution trajectory.

Output a JSON array with the following structure:

```json
[
  {{
    "threat_id": "string",
    "title": "string",
    "current_severity": "critical|high|medium|low",
    "trend": "escalating|stable|improving|dormant",
    "velocity": 0.0,
    "weaponisation_probability_30d": 0.0,
    "weaponisation_probability_60d": 0.0,
    "weaponisation_probability_90d": 0.0,
    "predicted_peak_severity": "critical|high|medium|low",
    "predicted_peak_date": "YYYY-MM-DD",
    "mitre_next_techniques": ["T1190", "T1059"],
    "kill_chain_stage": "initial_access|execution|persistence|privilege_escalation|defense_evasion|credential_access|discovery|lateral_movement|collection|exfiltration|impact",
    "remediation_deadline": "YYYY-MM-DD",
    "remediation_urgency": 0.0,
    "reasoning": "Brief explanation of prediction",
    "confidence": 0.0
  }}
]
```

Return ONLY the JSON array. No markdown fences.
""".strip()


class ThreatEvolutionAgent(BaseAgent):
    """
    Predicts how security threats will evolve over time.

    Uses the REASONING model tier for deep multi-step analysis.
    Stores predictions in Neo4j for the frontend timeline view.
    """

    name = "threat_evolution"
    description = "Predicts threat evolution trajectories using temporal graph analysis and NVIDIA NIM"
    model_tier = "reasoning"

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        repo = context.get("repository_full_name", "")
        all_findings = context.get("all_findings", [])

        if not all_findings and not repo:
            return AgentOutput(
                agent_name=self.name,
                status="skipped",
                summary="No findings or repository context available",
            )

        try:
            # ── Pull evolution data from Neo4j ──────────────────
            from app.knowledge.graph import KnowledgeGraphService
            from app.knowledge.threat_evolution import ThreatEvolutionEngine

            kg = KnowledgeGraphService()
            await kg.initialize()
            engine = ThreatEvolutionEngine(kg._driver)
            await engine.create_schema()

            # First, record current findings as new snapshots
            for finding in all_findings:
                fid = f"{repo}::{finding.get('cwe_id') or finding.get('title', '')}"
                await engine.record_threat_snapshot(
                    repo_full_name=repo,
                    threat_id=fid,
                    title=finding.get("title", "Unknown"),
                    severity=finding.get("severity", "medium"),
                    category=finding.get("category", "general"),
                    cwe_id=finding.get("cwe_id"),
                    cve_id=finding.get("cve_id"),
                    mitre_technique=finding.get("mitre_technique"),
                    confidence=finding.get("confidence", 0.5),
                    file_path=finding.get("file_path"),
                    agent_name=finding.get("agent_name", self.name),
                )

            # Fetch all evolution timelines
            timelines = await engine.get_all_timelines(repo)
            exploitability = await engine.get_exploitability_rankings(repo)

            # ── Build LLM prompt ────────────────────────────────
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            threat_summary_lines = []
            for tl in timelines[:20]:
                threat_summary_lines.append(
                    f"- [{tl['severity'].upper()}] {tl['title']} "
                    f"(ID: {tl['threat_id']}, trend: {tl['trend']}, "
                    f"snapshots: {tl['snap_count']})"
                )
            threat_summary = "\n".join(threat_summary_lines) or "No historical data yet."

            evolution_lines = []
            for tl in timelines[:10]:
                evolution_lines.append(
                    f"Threat: {tl['title']}\n"
                    f"  velocity={tl['velocity']}, trend={tl['trend']}, "
                    f"latest_score={tl['latest_score']}, "
                    f"mitre={tl.get('mitre', 'N/A')}, phase={tl.get('phase', 'N/A')}"
                )
            evolution_data = "\n".join(evolution_lines) or "No evolution history yet."

            cve_lines = []
            for f in all_findings[:10]:
                if f.get("cve_id"):
                    cve_lines.append(f"- {f['cve_id']}: {f.get('title', '')} ({f.get('severity', '')})")
            cve_context = "\n".join(cve_lines) or "No CVEs identified in this scan."

            prompt = _ANALYSIS_PROMPT.format(
                repo=repo, date=today,
                threat_summary=threat_summary,
                evolution_data=evolution_data,
                cve_context=cve_context,
            )

            # ── Call NVIDIA NIM ─────────────────────────────────
            response = await self.model_router.complete(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=prompt,
                tier="reasoning",
                temperature=0.1,
                max_tokens=4096,
            )

            raw = response.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip().rstrip("```").strip()

            trajectories: list[dict] = []
            try:
                trajectories = json.loads(raw)
                if not isinstance(trajectories, list):
                    trajectories = []
            except json.JSONDecodeError:
                logger.warning("ThreatEvolutionAgent: JSON parse failed", raw=raw[:200])

            # ── Store predictions in Neo4j ──────────────────────
            for traj in trajectories:
                tid = traj.get("threat_id", "")
                if not tid:
                    continue
                await engine.record_predicted_trajectory(
                    threat_id=tid,
                    repo_full_name=repo,
                    predictions=[traj],
                    model_used=response.model_used,
                    confidence=traj.get("confidence", 0.5),
                )

            await kg.close()

            # ── Convert to AgentFindings ────────────────────────
            findings: list[AgentFinding] = []
            for traj in trajectories:
                severity = traj.get("current_severity", "medium")
                urgency = traj.get("remediation_urgency", 0.0)
                wp30 = traj.get("weaponisation_probability_30d", 0.0)

                findings.append(AgentFinding(
                    title=f"[EVOLUTION] {traj.get('title', 'Unknown threat')}",
                    description=(
                        f"Trend: {traj.get('trend', 'stable')} | "
                        f"Velocity: {traj.get('velocity', 0):.3f} | "
                        f"Weaponisation in 30d: {wp30:.0%} | "
                        f"Peak: {traj.get('predicted_peak_severity', severity)} "
                        f"by {traj.get('predicted_peak_date', 'unknown')}"
                    ),
                    severity=severity,
                    category="threat_evolution",
                    confidence=traj.get("confidence", 0.5),
                    mitre_technique=(
                        traj.get("mitre_next_techniques", [""])[0]
                        if traj.get("mitre_next_techniques") else None
                    ),
                    recommendation=(
                        f"Remediate by {traj.get('remediation_deadline', 'ASAP')}. "
                        f"{traj.get('reasoning', '')}"
                    ),
                    reasoning=traj.get("reasoning", ""),
                ))

            # Top-urgency threats become critical findings
            for item in exploitability[:3]:
                if item.get("urgency_score", 0) > 0.8:
                    findings.append(AgentFinding(
                        title=f"[URGENT] {item.get('title', 'Threat')} requires immediate remediation",
                        description=(
                            f"Urgency score: {item['urgency_score']:.2f} | "
                            f"Trend: {item['trend']} | Velocity: {item['velocity']:.3f}"
                        ),
                        severity="critical",
                        category="threat_evolution",
                        confidence=0.85,
                        mitre_technique=item.get("mitre"),
                        recommendation="Immediate remediation required — threat is escalating rapidly",
                    ))

            return AgentOutput(
                agent_name=self.name,
                status="completed",
                findings=findings,
                confidence_score=0.85,
                model_used=response.model_used,
                tokens_used=response.tokens_used,
                summary=(
                    f"Analysed {len(timelines)} threats. "
                    f"{len([t for t in trajectories if t.get('trend') == 'escalating'])} escalating. "
                    f"{len([t for t in trajectories if t.get('weaponisation_probability_30d', 0) > 0.5])} "
                    f"likely to be weaponised in 30 days."
                ),
                metadata={
                    "trajectories": trajectories,
                    "exploitability_rankings": exploitability[:10],
                    "timeline_count": len(timelines),
                },
            )

        except Exception as exc:
            logger.error("ThreatEvolutionAgent failed", error=str(exc))
            return AgentOutput(
                agent_name=self.name,
                status="failed",
                error=str(exc),
            )
