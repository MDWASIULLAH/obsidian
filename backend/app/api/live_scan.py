"""Real repository scanning and fast, live knowledge graph APIs."""
from __future__ import annotations

import asyncio
import hashlib
import time
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

_SKIP_PREFIXES = (".git/", "node_modules/", ".next/", "dist/", "build/", "coverage/", "vendor/", "__pycache__/", ".venv/", "venv/")
_ALLOWED_NAMES = {"Dockerfile", "Makefile", "package.json", "requirements.txt", "pyproject.toml", "Pipfile", "Gemfile", "go.mod", "Cargo.toml"}
_ALLOWED_SUFFIXES = (".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".kt", ".swift", ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf", ".tf", ".tfvars", ".sh", ".bash", ".sql", ".xml", ".gradle", ".env.example")


def _eligible(path: str) -> bool:
    p = path.lower()
    if any(p.startswith(x) for x in _SKIP_PREFIXES):
        return False
    name = path.rsplit("/", 1)[-1]
    return name in _ALLOWED_NAMES or p.endswith(_ALLOWED_SUFFIXES)


async def _load_repository_sources(repo: Repository, ref: str) -> tuple[list[str], dict[str, str]]:
    from app.integrations.github_client import get_github_client
    gh = get_github_client()
    tree = await gh.get_repository_tree(repo.full_name, sha=ref, recursive=True)
    candidates = [x["path"] for x in tree if x.get("type") == "blob" and _eligible(x.get("path", ""))][:160]

    async def fetch(path: str):
        try:
            content = await gh.get_file_content(repo.full_name, path, ref=ref)
            if content is None or len(content) > 120_000:
                return None
            return path, content
        except Exception:
            return None

    results = await asyncio.gather(*(fetch(path) for path in candidates), return_exceptions=False)
    contents = {x[0]: x[1] for x in results if x}
    return candidates, contents


async def _run_pipeline_in_process(scan_id: str, state: dict[str, Any]) -> None:
    from app.agents.orchestrator import run_security_pipeline

    async with async_session_factory() as session:
        await session.execute(update(Scan).where(Scan.id == scan_id).values(status=ScanStatus.SCANNING.value, current_agent="orchestrator"))
        await session.commit()

    started = time.monotonic()
    try:
        final_state = await run_security_pipeline(state)
        findings = final_state.get("all_findings", [])
        counts = {level: sum(1 for f in findings if f.get("severity") == level) for level in ("critical", "high", "medium", "low")}
        score = final_state.get("security_score")
        if score is None:
            score = max(0, 100 - counts["critical"] * 20 - counts["high"] * 10 - counts["medium"] * 5 - counts["low"])

        async with async_session_factory() as session:
            await session.execute(update(Scan).where(Scan.id == scan_id).values(
                status=ScanStatus.COMPLETED.value,
                current_agent=None,
                total_findings=len(findings),
                critical_count=counts["critical"],
                high_count=counts["high"],
                medium_count=counts["medium"],
                low_count=counts["low"],
                patches_generated=len(final_state.get("generated_patches", [])),
                tests_generated=len(final_state.get("generated_tests", [])),
                security_score=int(score),
                confidence=int(final_state.get("overall_confidence", 0) * 100),
                threat_model=str(final_state.get("threat_model", {})),
                pr_url=final_state.get("pr_url"),
                duration_seconds=int(final_state.get("duration_seconds") or (time.monotonic() - started)),
            ))
            for item in findings:
                session.add(Finding(
                    scan_id=scan_id,
                    title=item.get("title", "Security finding"),
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
                    agent_name=item.get("agent_name", "orchestrator"),
                    reasoning=item.get("reasoning"),
                    recommendation=item.get("recommendation"),
                    citations=str(item.get("citations", [])),
                ))
            await session.commit()
    except Exception as exc:
        async with async_session_factory() as session:
            await session.execute(update(Scan).where(Scan.id == scan_id).values(status=ScanStatus.FAILED.value, current_agent=None, error_message=str(exc)[:2000]))
            await session.commit()


async def _prepare_and_run(scan_id: str, repository_id: str, ref: str, branch: str) -> None:
    """Fetch sources and run the pipeline after the Scan row already exists."""
    try:
        async with async_session_factory() as session:
            await session.execute(update(Scan).where(Scan.id == scan_id).values(status=ScanStatus.INDEXING.value, current_agent="repository-indexer"))
            await session.commit()

        async with async_session_factory() as session:
            repo_result = await session.execute(select(Repository).where(Repository.id == repository_id))
            repo = repo_result.scalar_one_or_none()
            if not repo:
                raise RuntimeError("Repository not found while preparing scan")
            changed_files, file_contents = await _load_repository_sources(repo, ref)

        if not file_contents:
            raise RuntimeError("GitHub returned no scannable source files")

        source_blob = "\n\n".join(f"===== FILE: {p} =====\n{c[:20_000]}" for p, c in file_contents.items())
        state: dict[str, Any] = {
            "repository_id": repository_id,
            "repository_full_name": repo.full_name,
            "commit_sha": ref,
            "branch": branch,
            "scan_id": scan_id,
            "trigger": "manual",
            "changed_files": changed_files,
            "file_contents": file_contents,
            "diff_content": source_blob[:120_000],
            "code_diff": source_blob[:120_000],
            "all_findings": scan_repository_files(file_contents),
        }

        from app.config import get_settings
        from app.tasks.celery_app import run_pipeline
        broker = get_settings().celery_broker_url
        if broker and "localhost" not in broker and "127.0.0.1" not in broker:
            run_pipeline.delay(scan_id, state)
        else:
            await _run_pipeline_in_process(scan_id, state)
    except Exception as exc:
        async with async_session_factory() as session:
            await session.execute(update(Scan).where(Scan.id == scan_id).values(status=ScanStatus.FAILED.value, current_agent=None, error_message=str(exc)[:2000]))
            await session.commit()


@router.post("/scans/real", response_model=ScanResponse)
async def trigger_real_scan(data: ScanCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> ScanResponse:
    """Create the scan immediately; GitHub indexing happens in the background."""
    result = await db.execute(select(Repository).where(Repository.id == data.repository_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    ref = data.commit_sha if data.commit_sha and data.commit_sha != "HEAD" else repo.default_branch
    branch = data.branch or repo.default_branch
    scan = Scan(repository_id=repo.id, commit_sha=ref, branch=branch, trigger=ScanTrigger.MANUAL, status=ScanStatus.QUEUED)
    db.add(scan)
    await db.flush()
    await db.commit()

    background_tasks.add_task(_prepare_and_run, str(scan.id), str(repo.id), ref, branch)
    return ScanResponse.model_validate(scan)


def _node_id(prefix: str, value: str) -> str:
    return f"{prefix}:{hashlib.sha1(value.encode()).hexdigest()[:12]}"


@router.get("/live-graph/{repo_id}")
async def live_graph(repo_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Fast repository-specific graph. Never blocks on GitHub/Neo4j during polling."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    scans_result = await db.execute(select(Scan).where(Scan.repository_id == repo.id).order_by(desc(Scan.created_at)).limit(12))
    scans = list(scans_result.scalars().all())
    findings_result = await db.execute(select(Finding).join(Scan, Finding.scan_id == Scan.id).where(Scan.repository_id == repo.id).order_by(desc(Finding.created_at)).limit(200))
    findings = list(findings_result.scalars().all())

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(node_id: str, label: str, node_type: str, properties: dict[str, Any] | None = None):
        if node_id in seen:
            return
        seen.add(node_id)
        nodes.append({"id": node_id, "label": label, "type": node_type, "properties": properties or {}})

    repo_node = f"repo:{repo.id}"
    add(repo_node, repo.full_name, "Repository", {"language": repo.language})

    for scan in scans:
        sid = f"scan:{scan.id}"
        status = getattr(scan.status, "value", str(scan.status))
        add(sid, f"Scan {str(scan.id)[:8]}", "Scan", {"status": status, "score": scan.security_score, "findings": scan.total_findings, "created_at": scan.created_at.isoformat() if scan.created_at else None})
        edges.append({"source": repo_node, "target": sid, "relationship": "SCANNED_BY"})

    file_nodes: dict[str, str] = {}
    agent_nodes: dict[str, str] = {}
    threat_nodes: dict[str, str] = {}

    for finding in findings:
        fid = f"finding:{finding.id}"
        add(fid, finding.title or "Security finding", "Vulnerability", {"severity": finding.severity, "confidence": finding.confidence, "file_path": finding.file_path, "cwe_id": finding.cwe_id, "cve_id": finding.cve_id, "recommendation": finding.recommendation})
        edges.extend([
            {"source": repo_node, "target": fid, "relationship": "HAS_FINDING"},
            {"source": f"scan:{finding.scan_id}", "target": fid, "relationship": "DISCOVERED"},
        ])
        threat_label = finding.mitre_technique or finding.owasp_category or finding.cwe_id or finding.category or "Security threat"
        tid = threat_nodes.setdefault(str(threat_label), _node_id("threat", str(threat_label)))
        add(tid, str(threat_label), "Threat", {"severity": finding.severity})
        edges.append({"source": fid, "target": tid, "relationship": "MAPS_TO_THREAT"})
        if finding.file_path:
            file_key = file_nodes.setdefault(finding.file_path, _node_id("file", finding.file_path))
            add(file_key, finding.file_path, "File", {"path": finding.file_path})
            edges.append({"source": repo_node, "target": file_key, "relationship": "CONTAINS"})
            edges.append({"source": file_key, "target": fid, "relationship": "HAS_VULNERABILITY"})
        if finding.agent_name:
            agent_key = agent_nodes.setdefault(finding.agent_name, _node_id("agent", finding.agent_name))
            add(agent_key, finding.agent_name, "Agent")
            edges.append({"source": agent_key, "target": fid, "relationship": "DISCOVERED"})
        if finding.recommendation:
            fix_key = _node_id("fix", finding.recommendation)
            add(fix_key, finding.recommendation[:80], "Fix", {"recommendation": finding.recommendation})
            edges.append({"source": fid, "target": fix_key, "relationship": "REMEDIATED_BY"})

    active_values = {ScanStatus.QUEUED.value, ScanStatus.INDEXING.value, ScanStatus.SCANNING.value, ScanStatus.PATCHING.value, ScanStatus.TESTING.value, ScanStatus.REVIEWING.value}
    active = [s for s in scans if getattr(s.status, "value", str(s.status)) in active_values]
    return {
        "repository_id": str(repo.id),
        "repository_name": repo.full_name,
        "nodes": nodes,
        "edges": edges,
        "meta": {"generated_at": datetime.now(timezone.utc).isoformat(), "active_scans": len(active), "finding_count": len(findings), "scan_count": len(scans)},
    }
