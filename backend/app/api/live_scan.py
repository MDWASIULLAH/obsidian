"""Production repository scanning and live graph endpoints."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session_factory, get_db
from app.models.finding import Finding
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus, ScanTrigger
from app.models.schemas import ScanCreate, ScanResponse
from app.scanning.static_scanner import scan_repository_files

router = APIRouter(tags=["live-scan"])

_SKIP_PREFIXES = (
    ".git/", "node_modules/", ".next/", "dist/", "build/", "coverage/",
    "vendor/", "__pycache__/", ".venv/", "venv/",
)
_ALLOWED_NAMES = {
    "Dockerfile", "Makefile", "Procfile", "package.json", "requirements.txt",
    "pyproject.toml", "Pipfile", "Gemfile", "go.mod", "Cargo.toml",
}
_ALLOWED_SUFFIXES = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb",
    ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".kt", ".swift",
    ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf", ".tf",
    ".tfvars", ".sh", ".bash", ".sql", ".xml", ".gradle", ".env.example",
)


def _eligible(path: str) -> bool:
    normalized = path.lower()
    if any(normalized.startswith(prefix) for prefix in _SKIP_PREFIXES):
        return False
    name = path.rsplit("/", 1)[-1]
    return name in _ALLOWED_NAMES or normalized.endswith(_ALLOWED_SUFFIXES)


async def _load_repository_sources(
    repo: Repository,
    ref: str,
) -> tuple[list[str], dict[str, str]]:
    from app.integrations.github_client import get_github_client

    gh = get_github_client()
    tree = await gh.get_repository_tree(repo.full_name, sha=ref, recursive=True)
    candidates = [
        item["path"]
        for item in tree
        if item.get("type") == "blob" and _eligible(item.get("path", ""))
    ][:120]

    async def fetch(path: str) -> tuple[str, str] | None:
        try:
            content = await gh.get_file_content(repo.full_name, path, ref=ref)
            if content is None or len(content) > 120_000:
                return None
            return path, content
        except Exception:
            return None

    results = await asyncio.gather(*(fetch(path) for path in candidates))
    contents = {item[0]: item[1] for item in results if item}
    return candidates, contents


async def _run_pipeline_in_process(scan_id: str, state: dict[str, Any]) -> None:
    """Run the real LangGraph pipeline when no external Celery worker exists."""
    from app.agents.orchestrator import run_security_pipeline

    async with async_session_factory() as session:
        await session.execute(
            update(Scan).where(Scan.id == scan_id).values(
                status=ScanStatus.SCANNING.value
            )
        )
        await session.commit()

    try:
        final_state = await run_security_pipeline(state)
        severity_counts: dict[str, int] = {}
        for item in final_state.get("all_findings", []):
            severity = item.get("severity", "info")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        async with async_session_factory() as session:
            await session.execute(
                update(Scan).where(Scan.id == scan_id).values(
                    status=ScanStatus.COMPLETED.value,
                    total_findings=len(final_state.get("all_findings", [])),
                    critical_count=severity_counts.get("critical", 0),
                    high_count=severity_counts.get("high", 0),
                    medium_count=severity_counts.get("medium", 0),
                    low_count=severity_counts.get("low", 0),
                    patches_generated=len(final_state.get("generated_patches", [])),
                    tests_generated=len(final_state.get("generated_tests", [])),
                    security_score=final_state.get("security_score", 0),
                    confidence=int(final_state.get("overall_confidence", 0) * 100),
                    threat_model=str(final_state.get("threat_model", {})),
                    pr_url=final_state.get("pr_url"),
                    duration_seconds=final_state.get("duration_seconds"),
                )
            )
            for item in final_state.get("all_findings", []):
                session.add(
                    Finding(
                        scan_id=scan_id,
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        severity=item.get("severity", "info"),
                        category=item.get("category", "vulnerability"),
                        confidence=item.get("confidence", 0.0),
                        file_path=item.get("file_path"),
                        line_start=item.get("line_start"),
                        line_end=item.get("line_end"),
                        code_snippet=item.get("code_snippet"),
                        cwe_id=item.get("cwe_id"),
                        cve_id=item.get("cve_id"),
                        owasp_category=item.get("owasp_category"),
                        mitre_technique=item.get("mitre_technique"),
                        agent_name=item.get("agent_name", ""),
                        reasoning=item.get("reasoning"),
                        recommendation=item.get("recommendation"),
                        citations=str(item.get("citations", [])),
                    )
                )
            await session.commit()
    except Exception as exc:
        async with async_session_factory() as session:
            await session.execute(
                update(Scan).where(Scan.id == scan_id).values(
                    status=ScanStatus.FAILED.value,
                    error_message=str(exc)[:2000],
                )
            )
            await session.commit()


@router.post("/scans/real", response_model=ScanResponse)
async def trigger_real_scan(
    data: ScanCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """Scan the actual repository contents instead of an empty/demo state."""
    result = await db.execute(
        select(Repository).where(Repository.id == data.repository_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    ref = data.commit_sha if data.commit_sha and data.commit_sha != "HEAD" else repo.default_branch
    try:
        changed_files, file_contents = await _load_repository_sources(repo, ref)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to read repository from GitHub: {exc}",
        ) from exc

    if not file_contents:
        raise HTTPException(
            status_code=502,
            detail="GitHub returned no scannable source files",
        )

    scan = Scan(
        repository_id=repo.id,
        commit_sha=ref,
        branch=data.branch or repo.default_branch,
        trigger=ScanTrigger.MANUAL,
        status=ScanStatus.QUEUED,
    )
    db.add(scan)
    await db.flush()
    await db.commit()

    full_scan_text = "\n\n".join(
        f"===== FILE: {path} =====\n{content[:20_000]}"
        for path, content in file_contents.items()
    )
    state: dict[str, Any] = {
        "repository_id": repo.id,
        "repository_full_name": repo.full_name,
        "commit_sha": ref,
        "branch": data.branch or repo.default_branch,
        "scan_id": scan.id,
        "trigger": "manual",
        "changed_files": changed_files,
        "file_contents": file_contents,
        "diff_content": full_scan_text[:120_000],
        "code_diff": full_scan_text[:120_000],
        "all_findings": scan_repository_files(file_contents),
    }

    # Prefer Celery when a real external broker is configured. Otherwise run
    # the same production pipeline inside the web process so scans never remain
    # permanently QUEUED simply because a worker service is missing.
    try:
        from app.config import get_settings
        from app.tasks.celery_app import run_pipeline

        broker = get_settings().celery_broker_url
        if broker and "localhost" not in broker and "127.0.0.1" not in broker:
            run_pipeline.delay(scan.id, state)
        else:
            background_tasks.add_task(_run_pipeline_in_process, scan.id, state)
    except Exception:
        background_tasks.add_task(_run_pipeline_in_process, scan.id, state)

    return ScanResponse.model_validate(scan)


@router.get("/live-graph/{repo_id}")
async def live_graph(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Build graph data from the real scan database on every request."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    scans_result = await db.execute(
        select(Scan)
        .where(Scan.repository_id == repo.id)
        .order_by(desc(Scan.created_at))
        .limit(8)
    )
    scans = list(scans_result.scalars().all())

    findings_result = await db.execute(
        select(Finding)
        .join(Scan, Finding.scan_id == Scan.id)
        .where(Scan.repository_id == repo.id)
        .order_by(desc(Finding.created_at))
        .limit(120)
    )
    findings = list(findings_result.scalars().all())

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    def add_node(
        node_id: str,
        label: str,
        node_type: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        nodes.append({
            "id": node_id,
            "label": label,
            "type": node_type,
            "properties": properties or {},
        })

    repo_node = f"repo:{repo.id}"
    add_node(repo_node, repo.full_name, "Repository", {"language": repo.language})

    for scan in scans:
        scan_node = f"scan:{scan.id}"
        add_node(
            scan_node,
            f"Scan {str(scan.id)[:8]}",
            "Scan",
            {
                "status": getattr(scan.status, "value", str(scan.status)),
                "security_score": scan.security_score,
                "findings": scan.total_findings,
                "created_at": scan.created_at.isoformat() if scan.created_at else None,
            },
        )
        edges.append({
            "source": repo_node,
            "target": scan_node,
            "relationship": "SCANNED_BY",
        })

    seen_files: set[str] = set()
    seen_agents: set[str] = set()
    for finding in findings:
        finding_node = f"finding:{finding.id}"
        add_node(
            finding_node,
            finding.title,
            "Vulnerability",
            {
                "severity": finding.severity,
                "confidence": finding.confidence,
                "cwe_id": finding.cwe_id,
                "cve_id": finding.cve_id,
                "file_path": finding.file_path,
                "line_start": finding.line_start,
            },
        )
        edges.append({"source": repo_node, "target": finding_node, "relationship": "HAS_FINDING"})
        edges.append({
            "source": f"scan:{finding.scan_id}",
            "target": finding_node,
            "relationship": "DISCOVERED",
        })

        if finding.file_path:
            file_key = f"file:{hashlib.sha1(finding.file_path.encode()).hexdigest()[:12]}"
            if finding.file_path not in seen_files:
                add_node(file_key, finding.file_path, "File", {"path": finding.file_path})
                seen_files.add(finding.file_path)
                edges.append({"source": repo_node, "target": file_key, "relationship": "CONTAINS"})
            edges.append({"source": file_key, "target": finding_node, "relationship": "HAS_VULNERABILITY"})

        if finding.agent_name:
            agent_key = f"agent:{hashlib.sha1(finding.agent_name.encode()).hexdigest()[:12]}"
            if finding.agent_name not in seen_agents:
                add_node(agent_key, finding.agent_name, "Agent", {})
                seen_agents.add(finding.agent_name)
                edges.append({"source": agent_key, "target": repo_node, "relationship": "ANALYZES"})
            edges.append({"source": agent_key, "target": finding_node, "relationship": "DISCOVERED"})

    active_statuses = {
        ScanStatus.QUEUED.value,
        ScanStatus.INDEXING.value,
        ScanStatus.SCANNING.value,
    }
    active_scans = sum(
        1 for scan in scans
        if getattr(scan.status, "value", str(scan.status)) in active_statuses
    )

    return {
        "repository_id": str(repo.id),
        "repository_name": repo.full_name,
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "active_scans": active_scans,
            "finding_count": len(findings),
        },
    }
