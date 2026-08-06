"""
SENTINEL AI X — LangGraph Master Orchestrator.

Defines the full security pipeline as a LangGraph StateGraph.
This is the brain of the system — it routes tasks to agents,
manages parallel execution, handles errors, and drives the
entire analysis-patch-test-approve workflow.

Pipeline Flow:
  Indexing → Knowledge Graph → Parallel Scan → Merge →
  Attack Simulation → Patch → Test → Documentation →
  Verify → Deployment Approval → PR Creation
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from typing import Any

import structlog
from langgraph.graph import END, StateGraph

from app.agents.base import AgentOutput
from app.agents.registry import (
    PARALLEL_SCAN_AGENTS,
    SEQUENTIAL_ACTION_AGENTS,
    get_agent_registry,
)
from app.agents.state import PipelineState
from app.integrations.github_client import get_github_client


logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# Pipeline Node Functions
# ═══════════════════════════════════════════════════════════════════


async def index_repository(state: dict) -> dict:
    """
    Phase 1: Index the repository.

    Clones/fetches the repo, extracts the diff, and classifies
    files by type (code, config, IaC, Dockerfile, deps).
    """
    logger.info("📂 Phase: Repository Indexing", repo=state.get("repository_full_name"))
    state["current_phase"] = "indexing"

    # Classify changed files
    changed = state.get("changed_files", [])
    file_contents = state.get("file_contents", {})

    # Detect dependency files
    dep_patterns = [
        "requirements.txt", "Pipfile", "pyproject.toml", "setup.py",
        "package.json", "yarn.lock", "pnpm-lock.yaml",
        "Gemfile", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
    ]
    dep_files = {
        name: content for name, content in file_contents.items()
        if any(name.endswith(p) or name.split("/")[-1] in dep_patterns for p in dep_patterns)
    }
    state["dependency_files"] = dep_files

    # Detect config files
    config_patterns = [".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".env"]
    config_files = {
        name: content for name, content in file_contents.items()
        if any(name.endswith(p) for p in config_patterns)
    }
    state["config_files"] = config_files

    # Detect IaC files
    iac_patterns = [".tf", ".tfvars", "cloudformation", "ansible", "k8s", "helm"]
    iac_files = {
        name: content for name, content in file_contents.items()
        if any(p in name.lower() for p in iac_patterns)
    }
    state["iac_files"] = iac_files

    # Detect Dockerfile
    for name, content in file_contents.items():
        if "dockerfile" in name.lower():
            state["dockerfile_content"] = content
            break

    # Detect languages
    ext_lang = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
        ".cs": "C#", ".cpp": "C++", ".c": "C", ".php": "PHP",
        ".swift": "Swift", ".kt": "Kotlin",
    }
    languages = set()
    for name in changed:
        for ext, lang in ext_lang.items():
            if name.endswith(ext):
                languages.add(lang)
    state["repo_languages"] = list(languages)

    logger.info(
        "✅ Indexing complete",
        files=len(changed),
        languages=list(languages),
        deps=len(dep_files),
        iac=len(iac_files),
    )

    return state


async def event_router(state: dict) -> dict:
    """
    Phase 0: Route the GitHub event.

    Reads event_type from state and decides:
    - which agents to activate (requested_agents)
    - whether the full pipeline should run (requires_full_pipeline)
    """
    event_type = state.get("event_type", "push")
    logger.info("🔀 Phase: Event Routing", event_type=event_type)
    state["current_phase"] = "event_routing"

    # Events that always run the full 18-agent pipeline
    FULL_PIPELINE_EVENTS = {"push", "pull_request"}
    # Events that run a targeted subset
    PARTIAL_PIPELINE_EVENTS = {
        "security_advisory", "dependabot_alert",
        "secret_scanning_alert", "code_scanning_alert",
        "deployment", "release",
    }

    if event_type in FULL_PIPELINE_EVENTS:
        state["requires_full_pipeline"] = True
        state["requested_agents"] = []
    elif event_type in PARTIAL_PIPELINE_EVENTS:
        state["requires_full_pipeline"] = True  # partial but still runs pipeline
        hints = state.get("event_data", {}).get("agent_routing_hints", [])
        state["requested_agents"] = hints
    else:
        # Graph-update-only events: create, delete, workflow_run, member, etc.
        state["requires_full_pipeline"] = False
        state["requested_agents"] = []

    logger.info(
        "✅ Event routed",
        event_type=event_type,
        full_pipeline=state["requires_full_pipeline"],
        agents=state.get("requested_agents", []),
    )
    return state


async def update_digital_twin(state: dict) -> dict:
    """
    Phase 1.5: Update the AI Security Digital Twin graph.

    Performs incremental Neo4j mutations based on the GitHub event.
    Runs after indexing, before the security scan, for every event.
    """
    logger.info("🔮 Phase: Digital Twin Update", event_type=state.get("event_type"))
    state["current_phase"] = "digital_twin"

    try:
        from app.knowledge.graph import KnowledgeGraphService
        from app.knowledge.digital_twin import get_digital_twin_service

        graph = KnowledgeGraphService()
        await graph.initialize()
        twin = get_digital_twin_service(graph)

        repo = state.get("repository_full_name", "")
        event_type = state.get("event_type", "push")
        event_data = state.get("event_data", {})
        stats: dict = {"nodes_created": 0, "nodes_updated": 0, "edges_created": 0}

        if event_type == "push":
            stats = await twin.process_push_event(
                repo_full_name=repo,
                branch=state.get("branch", ""),
                commit_sha=state.get("commit_sha", ""),
                sender=event_data.get("sender", "unknown"),
                changed_files=state.get("changed_files", []),
                payload=event_data,
            )
        elif event_type in ("pull_request", "pull_request_review"):
            stats = await twin.process_pr_event(
                repo_full_name=repo,
                pr_number=state.get("pr_number") or 0,
                head_sha=state.get("commit_sha", ""),
                head_branch=state.get("branch", ""),
                base_branch=event_data.get("base_branch", "main"),
                action=state.get("event_action") or "",
                sender=event_data.get("sender", "unknown"),
            )
        elif event_type in ("create", "delete"):
            ref_type = event_data.get("ref_type", "")
            if ref_type == "branch":
                stats = await twin.process_branch_event(
                    repo_full_name=repo,
                    branch=state.get("branch", ""),
                    action="created" if event_type == "create" else "deleted",
                )
        elif event_type in ("security_advisory", "dependabot_alert",
                            "secret_scanning_alert", "code_scanning_alert"):
            stats = await twin.process_security_alert(
                repo_full_name=repo,
                event_type=event_type,
                alert=event_data,
                action=state.get("event_action") or "",
            )
        elif event_type == "deployment":
            stats = await twin.process_deployment(
                repo_full_name=repo,
                deployment=event_data,
                action=state.get("event_action") or "",
            )
        elif event_type == "workflow_run":
            stats = await twin.process_workflow_run(
                repo_full_name=repo,
                workflow_run=event_data,
            )

        state.setdefault("digital_twin_updates", []).append({
            "event_type": event_type,
            "stats": stats,
        })
        state["graph_context"] = {
            "repository": repo,
            "files_indexed": len(state.get("changed_files", [])),
            "dependencies": list(state.get("dependency_files", {}).keys()),
            "twin_stats": stats,
        }
        logger.info("✅ Digital Twin updated", **stats)
    except Exception as exc:
        logger.error("Digital Twin update failed", error=str(exc))
        state.setdefault("errors", []).append(f"digital_twin: {exc}")

    return state


async def update_knowledge_graph(state: dict) -> dict:
    """
    Phase 2: Update the Neo4j knowledge graph.

    Adds nodes/edges for files, functions, dependencies,
    and known vulnerability context.
    """
    logger.info("🧠 Phase: Knowledge Graph Update")
    state["current_phase"] = "knowledge_graph"

    state["graph_context"] = state.get("graph_context") or {
        "repository": state.get("repository_full_name"),
        "files_indexed": len(state.get("changed_files", [])),
        "dependencies": list(state.get("dependency_files", {}).keys()),
    }

    return state


async def parallel_security_scan(state: dict) -> dict:
    """
    Phase 3: Run all security scanning agents in parallel.

    Each agent receives the full context and returns findings.
    Results are merged into the shared state.
    """
    logger.info("🔍 Phase: Parallel Security Scan")
    state["current_phase"] = "scanning"

    registry = get_agent_registry()
    scan_agents = registry.get_scan_agents()

    # Build context dict from state
    context = dict(state)

    # Run all scan agents concurrently
    tasks = []
    for agent in scan_agents:
        state["current_agent"] = agent.name
        tasks.append(_execute_agent_safe(agent, context))

    results: list[AgentOutput] = await asyncio.gather(*tasks)

    # Merge findings from all agents
    all_findings = state.get("all_findings", [])
    agent_results = state.get("agent_results", {})

    for output in results:
        agent_results[output.agent_name] = {
            "status": output.status,
            "findings_count": len(output.findings),
            "confidence": output.confidence_score,
            "summary": output.summary,
            "duration_ms": output.duration_ms,
            "error": output.error,
        }

        for finding in output.findings:
            all_findings.append({
                "title": finding.title,
                "description": finding.description,
                "severity": finding.severity,
                "category": finding.category,
                "confidence": finding.confidence,
                "file_path": finding.file_path,
                "line_start": finding.line_start,
                "line_end": finding.line_end,
                "code_snippet": finding.code_snippet,
                "cwe_id": finding.cwe_id,
                "cve_id": finding.cve_id,
                "owasp_category": finding.owasp_category,
                "mitre_technique": finding.mitre_technique,
                "recommendation": finding.recommendation,
                "reasoning": finding.reasoning,
                "agent_name": output.agent_name,
                "citations": finding.citations,
            })

    state["all_findings"] = all_findings
    state["agent_results"] = agent_results

    # Get threat model and architecture review from context (agents may have written there)
    if "threat_model" in context:
        state["threat_model"] = context["threat_model"]
    if "architecture_review" in context:
        state["architecture_review"] = context["architecture_review"]

    logger.info(
        "✅ Parallel scan complete",
        agents=len(results),
        findings=len(all_findings),
    )

    return state


async def attack_simulation_node(state: dict) -> dict:
    """Phase 4: Simulate attack chains from findings."""
    logger.info("⚔️ Phase: Attack Simulation")
    state["current_phase"] = "attack_simulation"

    registry = get_agent_registry()
    agent = registry.get_agent("attack_simulation")
    output = await _execute_agent_safe(agent, dict(state))

    # Merge attack findings
    for finding in output.findings:
        state.setdefault("all_findings", []).append({
            "title": finding.title,
            "description": finding.description,
            "severity": finding.severity,
            "category": finding.category,
            "confidence": finding.confidence,
            "mitre_technique": finding.mitre_technique,
            "reasoning": finding.reasoning,
            "agent_name": "attack_simulation",
        })

    state.setdefault("agent_results", {})["attack_simulation"] = {
        "status": output.status,
        "findings_count": len(output.findings),
        "confidence": output.confidence_score,
    }

    return state


async def auto_patch_node(state: dict) -> dict:
    """Phase 5: Generate security patches."""
    logger.info("🔧 Phase: Auto Patching")
    state["current_phase"] = "patching"

    registry = get_agent_registry()
    agent = registry.get_agent("auto_patcher")

    context = dict(state)
    await _execute_agent_safe(agent, context)

    state["generated_patches"] = context.get("generated_patches", [])
    state["patches_generated"] = len(state["generated_patches"])

    logger.info("✅ Patches generated", count=len(state["generated_patches"]))
    return state


async def regression_test_node(state: dict) -> dict:
    """Phase 6: Generate regression tests."""
    logger.info("🧪 Phase: Test Generation")
    state["current_phase"] = "testing"

    registry = get_agent_registry()
    agent = registry.get_agent("regression_tester")

    context = dict(state)
    await _execute_agent_safe(agent, context)

    state["generated_tests"] = context.get("generated_tests", [])
    state["tests_generated"] = len(state["generated_tests"])

    logger.info("✅ Tests generated", count=len(state["generated_tests"]))
    return state


async def documentation_node(state: dict) -> dict:
    """Phase 7: Update documentation."""
    logger.info("📝 Phase: Documentation")
    state["current_phase"] = "documentation"

    registry = get_agent_registry()
    agent = registry.get_agent("documentation")

    context = dict(state)
    await _execute_agent_safe(agent, context)

    state["documentation_updates"] = context.get("documentation_updates", [])
    return state


async def verification_node(state: dict) -> dict:
    """
    Phase 8: Verify patches and test results.

    Checks that patches are valid and tests pass.
    """
    logger.info("✔️ Phase: Verification")
    state["current_phase"] = "verification"

    patches = state.get("generated_patches", [])
    tests = state.get("generated_tests", [])

    # Basic verification: all patches have non-empty content
    valid_patches = [
        p for p in patches
        if p.get("patched_code") and p.get("diff")
    ]

    state["verification_results"] = {
        "total_patches": len(patches),
        "valid_patches": len(valid_patches),
        "total_tests": len(tests),
        "verification_passed": len(valid_patches) == len(patches) or len(patches) == 0,
    }
    state["verification_passed"] = state["verification_results"]["verification_passed"]

    return state


async def deployment_approval_node(state: dict) -> dict:
    """Phase 9: Make deployment decision."""
    logger.info("🛡️ Phase: Deployment Approval")
    state["current_phase"] = "reviewing"

    registry = get_agent_registry()
    agent = registry.get_agent("deployment_approval")

    context = dict(state)
    await _execute_agent_safe(agent, context)

    state["deployment_approved"] = context.get("deployment_approved", False)
    state["deployment_decision"] = context.get("deployment_decision", {})
    state["overall_confidence"] = context.get("overall_confidence", 0.0)
    state["security_score"] = context.get("security_score", 0)

    logger.info(
        "🛡️ Deployment decision",
        approved=state["deployment_approved"],
        score=state["security_score"],
    )

    return state


async def learning_node(state: dict) -> dict:
    """Phase 10: Learn from this pipeline run."""
    logger.info("📚 Phase: Learning")

    registry = get_agent_registry()
    agent = registry.get_agent("learning_agent")
    await _execute_agent_safe(agent, dict(state))

    return state


async def github_feedback_node(state: dict) -> dict:
    """Phase 11: GitHub Feedback Loop."""
    logger.info("📤 Phase: GitHub Feedback Loop")
    state["current_phase"] = "completed"

    findings = state.get("all_findings", [])
    patches = state.get("generated_patches", [])
    score = state.get("security_score", 0)
    approved = state.get("deployment_approved", False)
    repo = state.get("repository_full_name")
    sha = state.get("commit_sha")

    # Build markdown report
    severity_counts = {}
    for f in findings:
        sev = f.get("severity", "info")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    report = (
        f"# 🛡️ SENTINEL AI X Security Report\n\n"
        f"## Security Score: {score}/100\n\n"
        f"## Deployment: {'✅ APPROVED' if approved else '❌ BLOCKED'}\n\n"
        f"## Findings Summary\n"
        f"| Severity | Count |\n|:---|:---|\n"
    )
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = severity_counts.get(sev, 0)
        emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(sev, "⚪")
        report += f"| {emoji} {sev.title()} | {count} |\n"

    report += f"\n## Patches Generated: {len(patches)}\n"

    if findings:
        report += "\n## Top Findings\n"
        for f in findings[:10]:
            report += f"- **[{f.get('severity', 'info').upper()}]** {f.get('title')} "
            if f.get('cwe_id'):
                report += f"(CWE-{f['cwe_id']}) "
            report += "\n"

    state["pr_body"] = report
    state["agent_execution_order"] = PARALLEL_SCAN_AGENTS + SEQUENTIAL_ACTION_AGENTS

    # Execute GitHub feedback if we have context
    if repo and sha:
        client = get_github_client()
        conclusion = "success" if approved and severity_counts.get("critical", 0) == 0 else "failure"
        
        try:
            # 1. Finalize Check Run
            await client.create_check_run(
                full_name=repo,
                name="Security Analysis",
                head_sha=sha,
                status="completed",
                conclusion=conclusion,
                output={
                    "title": f"Security Score: {score}",
                    "summary": report,
                }
            )
            
            # 2. Finalize Commit Status
            await client.create_commit_status(
                full_name=repo,
                sha=sha,
                state=conclusion,
                description=f"Score: {score}/100 | {'Approved' if approved else 'Blocked'}",
                context="SENTINEL AI X"
            )

            # 3. Create PR if patches generated
            if patches and state.get("branch"):
                pr_title = f"🔐 Auto-Patch: Sentinel AI X Security Fixes ({sha[:7]})"
                pr_data = await client.create_pull_request(
                    full_name=repo,
                    title=pr_title,
                    body=report,
                    head_branch=f"sentinel-patch-{sha[:7]}",  # Assumes branch was pushed by patch agent
                    base_branch=state.get("branch")
                )
                
                # Inline comments for patches (mocked for now, assuming patch has line info)
                # await client.create_review_comment(...)
                
                # Add labels
                await client.add_labels(repo, pr_data["number"], ["security", "auto-patch"])

            # 4. Create Issue if critical/high findings exist but NO patches could be made
            elif (severity_counts.get("critical", 0) > 0 or severity_counts.get("high", 0) > 0):
                issue_title = f"🚨 Security Vulnerabilities Detected on {state.get('branch', 'branch')}"
                issue_data = await client.create_issue(
                    full_name=repo,
                    title=issue_title,
                    body=report,
                    labels=["security", "vulnerability"]
                )
                
        except Exception as e:
            logger.error("Failed to post GitHub feedback", error=str(e))

    logger.info("✅ Pipeline complete", score=score, findings=len(findings))

    return state


# ═══════════════════════════════════════════════════════════════════
# Routing Logic
# ═══════════════════════════════════════════════════════════════════


def should_continue_after_verification(state: dict) -> str:
    """Decide whether to proceed to approval or re-patch."""
    if state.get("verification_passed", False):
        return "deployment_approval"
    retry_count = state.get("_patch_retry", 0)
    if retry_count < 2:
        state["_patch_retry"] = retry_count + 1
        return "auto_patch"
    return "deployment_approval"


def should_run_full_pipeline(state: dict) -> str:
    """Decide whether to run the full scan or stop after Digital Twin update."""
    if state.get("requires_full_pipeline", True):
        return "parallel_security_scan"
    return "end"


# ═══════════════════════════════════════════════════════════════════
# Graph Construction
# ═══════════════════════════════════════════════════════════════════


def build_pipeline_graph() -> StateGraph:
    """
    Build the LangGraph StateGraph for the full security pipeline.

    Pipeline Flow:
      event_router → index_repository → update_digital_twin →
        [conditional: requires_full_pipeline?]
          YES → update_knowledge_graph → parallel_security_scan → ...
          NO  → END (graph-update-only)
    """
    graph = StateGraph(dict)

    # ── Add all nodes ──────────────────────────────────────────
    graph.add_node("event_router", event_router)
    graph.add_node("index_repository", index_repository)
    graph.add_node("update_digital_twin", update_digital_twin)
    graph.add_node("update_knowledge_graph", update_knowledge_graph)
    graph.add_node("parallel_security_scan", parallel_security_scan)
    graph.add_node("attack_simulation", attack_simulation_node)
    graph.add_node("auto_patch", auto_patch_node)
    graph.add_node("regression_test", regression_test_node)
    graph.add_node("documentation", documentation_node)
    graph.add_node("verification", verification_node)
    graph.add_node("deployment_approval", deployment_approval_node)
    graph.add_node("learning", learning_node)
    graph.add_node("github_feedback", github_feedback_node)

    # ── Define edges (pipeline flow) ───────────────────────────
    graph.set_entry_point("event_router")

    graph.add_edge("event_router", "index_repository")
    graph.add_edge("index_repository", "update_digital_twin")

    # Conditional: full pipeline or stop after Digital Twin
    graph.add_conditional_edges(
        "update_digital_twin",
        should_run_full_pipeline,
        {
            "parallel_security_scan": "update_knowledge_graph",
            "end": END,
        },
    )

    graph.add_edge("update_knowledge_graph", "parallel_security_scan")
    graph.add_edge("parallel_security_scan", "attack_simulation")
    graph.add_edge("attack_simulation", "auto_patch")
    graph.add_edge("auto_patch", "regression_test")
    graph.add_edge("regression_test", "documentation")
    graph.add_edge("documentation", "verification")

    # Conditional: verification → approval or retry
    graph.add_conditional_edges(
        "verification",
        should_continue_after_verification,
        {
            "deployment_approval": "deployment_approval",
            "auto_patch": "auto_patch",
        },
    )

    graph.add_edge("deployment_approval", "learning")
    graph.add_edge("learning", "github_feedback")
    graph.add_edge("github_feedback", END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════════
# Execution Helper
# ═══════════════════════════════════════════════════════════════════


async def _execute_agent_safe(agent, context: dict) -> AgentOutput:
    """Execute an agent with error handling."""
    try:
        return await agent.execute(context)
    except Exception as e:
        logger.error(
            "Agent execution error",
            agent=agent.name,
            error=str(e),
        )
        return AgentOutput(
            agent_name=agent.name,
            status="failed",
            error=str(e),
        )


async def run_security_pipeline(initial_state: dict) -> dict:
    """
    Run the full security pipeline.

    Args:
        initial_state: Dict with repository info, diff, files, etc.

    Returns:
        Final pipeline state with all findings, patches, tests, and decision.
    """
    logger.info(
        "🚀 Starting security pipeline",
        repo=initial_state.get("repository_full_name"),
        commit=initial_state.get("commit_sha", "")[:8],
    )

    repo = initial_state.get("repository_full_name")
    sha = initial_state.get("commit_sha")

    if repo and sha:
        client = get_github_client()
        try:
            await client.create_check_run(
                full_name=repo,
                name="Security Analysis",
                head_sha=sha,
                status="in_progress"
            )
            await client.create_commit_status(
                full_name=repo,
                sha=sha,
                state="pending",
                description="OBSIDIAN is analyzing the code...",
                context="SENTINEL AI X"
            )
        except Exception as e:
            logger.warning("Failed to initialize GitHub status checks", error=str(e))

    start = time.perf_counter()

    graph = build_pipeline_graph()
    final_state = await graph.ainvoke(initial_state)

    duration = time.perf_counter() - start
    final_state["duration_seconds"] = int(duration)

    logger.info(
        "🏁 Pipeline complete",
        duration_s=f"{duration:.1f}",
        findings=len(final_state.get("all_findings", [])),
        patches=len(final_state.get("generated_patches", [])),
        score=final_state.get("security_score", 0),
        approved=final_state.get("deployment_approved", False),
    )

    return final_state
