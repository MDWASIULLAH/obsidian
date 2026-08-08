"""
OBSIDIAN — REST API Router.

Mounts all API endpoints under /api/v1.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus, ScanTrigger
from app.models.finding import Finding
from app.models.agent_run import AgentRun
from app.models.patch import Patch
from app.models.github_event import GitHubEvent, ProcessingStatus
from app.models.schemas import (
    AgentInfo,
    DashboardOverview,
    DigitalTwinNodeDetail,
    DigitalTwinResponse,
    DigitalTwinSearchResult,
    FindingResponse,
    GitHubEventResponse,
    GraphData,
    HealthCheck,
    PaginatedResponse,
    PatchResponse,
    RepositoryCreate,
    RepositoryResponse,
    ScanCreate,
    ScanResponse,
    ScanSummary,
    WebhookPayload,
    ThreatTimelineResponse,
    ThreatTimelineSummary,
    ThreatTrajectoryResponse,
    ExploitabilityRankingResponse,
    AttackChainResponse,
    AttackMovieResponse,
    BlastRadiusResponse,
    BusinessImpactRequest,
    BusinessImpactResponse,
    TimelineSnapshotSummary,
    TimelineSnapshotDetail,
    TimelineDiffResponse,
    PostureTrendResponse,
)

logger = structlog.get_logger()

api_router = APIRouter()


# ═══════════════════════════════════════════════════════════════════
# Webhooks
# ═══════════════════════════════════════════════════════════════════


# Events that should trigger a Scan record and pipeline
_PIPELINE_EVENTS = {
    "push", "pull_request", "security_advisory",
    "dependabot_alert", "secret_scanning_alert",
    "code_scanning_alert", "deployment", "release",
}

_EVENT_TO_TRIGGER: dict[str, ScanTrigger] = {
    "push": ScanTrigger.PUSH,
    "pull_request": ScanTrigger.PULL_REQUEST,
    "security_advisory": ScanTrigger.MANUAL,
    "dependabot_alert": ScanTrigger.MANUAL,
    "secret_scanning_alert": ScanTrigger.MANUAL,
    "code_scanning_alert": ScanTrigger.MANUAL,
    "deployment": ScanTrigger.MANUAL,
    "release": ScanTrigger.MANUAL,
}


@api_router.post("/webhooks/github", tags=["webhooks"])
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive all GitHub webhook events.

    Handles 22 event types. Every event:
      1. Verifies HMAC-SHA256 signature
      2. Is persisted to github_events table (event sourcing)
      3. Triggers a Celery task for async processing
      4. Returns immediately (webhook must respond in <10s)
    """
    from app.integrations.github_client import get_github_client

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    event_type = request.headers.get("X-GitHub-Event", "")

    client = get_github_client()
    if not client.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = json.loads(body)
    payload_hash = hashlib.sha256(body).hexdigest()

    # Parse the event into a normalised structure
    event_data = client.parse_event_payload(event_type, payload)
    repo_full_name = event_data.repository_full_name

    logger.info(
        "Webhook received",
        event=event_type,
        action=event_data.action,
        repo=repo_full_name,
    )

    # Handle GitHub App installation lifecycle before repository-scoped processing.
    if event_type in ("installation", "installation_repositories"):
        from app.models.github_installation import GitHubInstallation

        installation = payload.get("installation") or {}
        installation_id = installation.get("id")
        account = installation.get("account") or {}

        if installation_id:
            result = await db.execute(
                select(GitHubInstallation).where(
                    GitHubInstallation.installation_id == installation_id
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = GitHubInstallation(installation_id=installation_id)
                db.add(record)

            record.account_login = account.get("login") or "unknown"
            record.account_type = account.get("type") or "User"
            record.target_type = installation.get("target_type")
            record.repository_selection = installation.get("repository_selection") or "selected"
            record.permissions = installation.get("permissions") or {}
            record.events = installation.get("events") or []
            record.is_active = event_data.action != "deleted"

            repo_payloads = []
            if event_type == "installation":
                repo_payloads = payload.get("repositories") or []
            elif event_data.action == "added":
                repo_payloads = payload.get("repositories_added") or []

            for repo_raw in repo_payloads:
                full_name = repo_raw.get("full_name")
                if not full_name:
                    continue
                repo_result = await db.execute(
                    select(Repository).where(Repository.github_id == repo_raw.get("id", 0))
                )
                repo = repo_result.scalar_one_or_none()
                if repo is None:
                    repo = Repository(github_id=repo_raw.get("id", 0), full_name=full_name)
                    db.add(repo)
                owner, name = full_name.split("/", 1)
                repo.full_name = full_name
                repo.name = repo_raw.get("name") or name
                repo.owner = owner
                repo.default_branch = repo_raw.get("default_branch") or "main"
                repo.clone_url = repo_raw.get("clone_url") or ""
                repo.description = repo_raw.get("description")
                repo.language = repo_raw.get("language")
                repo.installation_id = installation_id
                repo.is_active = True

            if event_type == "installation_repositories" and event_data.action == "removed":
                for repo_raw in payload.get("repositories_removed") or []:
                    repo_result = await db.execute(
                        select(Repository).where(Repository.github_id == repo_raw.get("id", 0))
                    )
                    repo = repo_result.scalar_one_or_none()
                    if repo:
                        repo.is_active = False

            await db.commit()

        return {"status": "installation_synced", "event": event_type}

    if event_type == "ping":
        return {"status": "acknowledged", "event": event_type}

    # Find the repository in our DB (must be tracked to process)
    result = await db.execute(
        select(Repository).where(Repository.full_name == repo_full_name)
    )
    repo = result.scalar_one_or_none()

    if not repo and not repo_full_name:
        return {"status": "repo_not_tracked", "event": event_type}

    # Auto-register repositories discovered through any repository-scoped App event.
    if not repo and repo_full_name:
        repo_raw = payload.get("repository", {})
        repo = Repository(
            github_id=repo_raw.get("id", 0),
            full_name=repo_full_name,
            name=repo_raw.get("name", ""),
            owner=repo_raw.get("owner", {}).get("login", ""),
            default_branch=repo_raw.get("default_branch", "main"),
            clone_url=repo_raw.get("clone_url", ""),
            description=repo_raw.get("description"),
            language=repo_raw.get("language"),
        )
        db.add(repo)
        await db.flush()

    if not repo:
        return {"status": "repo_not_tracked", "event": event_type}

    # Persist event for audit trail and Time Machine
    gh_event = GitHubEvent(
        event_type=event_type,
        action=event_data.action,
        delivery_id=delivery_id or None,
        repository_id=repo.id,
        sender=event_data.sender,
        payload_hash=payload_hash,
        payload=json.dumps(payload),
        commit_sha=event_data.commit_sha,
        branch=event_data.branch,
        pr_number=event_data.pr_number,
        processing_status=ProcessingStatus.PENDING.value,
    )
    db.add(gh_event)
    await db.flush()
    await db.commit()

    # Dispatch to Celery for async processing
    from app.tasks.celery_app import process_github_event
    process_github_event.apply_async(
        args=[gh_event.id, repo.id, event_type, payload, {
            "branch": event_data.branch,
            "commit_sha": event_data.commit_sha,
            "pr_number": event_data.pr_number,
            "changed_files": event_data.changed_files,
            "requires_full_pipeline": event_data.requires_full_pipeline,
            "agent_routing_hints": event_data.agent_routing_hints,
            "sender": event_data.sender,
            "action": event_data.action,
            "extra": event_data.extra,
        }],
        queue="events",
    )

    return {
        "status": "accepted",
        "event": event_type,
        "delivery_id": delivery_id,
        "event_id": gh_event.id,
        "requires_pipeline": event_data.requires_full_pipeline,
    }


async def _handle_push(payload: dict, db: AsyncSession) -> dict:
    """Handle a push webhook — trigger full security pipeline."""
    repo_data = payload.get("repository", {})
    full_name = repo_data.get("full_name", "")
    commit_sha = payload.get("after", "")
    branch = payload.get("ref", "").replace("refs/heads/", "")

    # Find or create repository
    result = await db.execute(
        select(Repository).where(Repository.full_name == full_name)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        repo = Repository(
            github_id=repo_data.get("id", 0),
            full_name=full_name,
            name=repo_data.get("name", ""),
            owner=repo_data.get("owner", {}).get("login", ""),
            default_branch=repo_data.get("default_branch", "main"),
            clone_url=repo_data.get("clone_url", ""),
            description=repo_data.get("description"),
            language=repo_data.get("language"),
        )
        db.add(repo)
        await db.flush()

    # Create scan record
    scan = Scan(
        repository_id=repo.id,
        commit_sha=commit_sha,
        branch=branch,
        trigger=ScanTrigger.PUSH,
        status=ScanStatus.QUEUED,
    )
    db.add(scan)
    await db.flush()

    # Get diff data from GitHub
    from app.integrations.github_client import get_github_client
    gh = get_github_client()
    diff_data = await gh.get_commit_diff(full_name, commit_sha)

    # Build initial pipeline state
    initial_state = {
        "repository_id": repo.id,
        "repository_full_name": full_name,
        "commit_sha": commit_sha,
        "branch": branch,
        "scan_id": scan.id,
        "trigger": "push",
        "diff_content": diff_data.get("diff", ""),
        "changed_files": diff_data.get("changed_files", []),
        "file_contents": diff_data.get("file_contents", {}),
    }

    # Enqueue pipeline task
    from app.tasks.celery_app import run_pipeline
    run_pipeline.delay(scan.id, initial_state)

    logger.info("Pipeline queued", scan_id=scan.id, repo=full_name)
    return {"status": "pipeline_queued", "scan_id": scan.id}


async def _handle_pull_request(payload: dict, db: AsyncSession) -> dict:
    """Handle a pull_request webhook."""
    action = payload.get("action", "")
    if action not in ("opened", "synchronize"):
        return {"status": "action_ignored", "action": action}

    pr = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})
    full_name = repo_data.get("full_name", "")

    result = await db.execute(
        select(Repository).where(Repository.full_name == full_name)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        return {"status": "repo_not_tracked"}

    scan = Scan(
        repository_id=repo.id,
        commit_sha=pr.get("head", {}).get("sha", ""),
        branch=pr.get("head", {}).get("ref", ""),
        trigger=ScanTrigger.PULL_REQUEST,
        pr_number=pr.get("number"),
        status=ScanStatus.QUEUED,
    )
    db.add(scan)
    await db.flush()

    from app.tasks.celery_app import run_pipeline
    run_pipeline.delay(scan.id, {
        "repository_id": repo.id,
        "repository_full_name": full_name,
        "commit_sha": scan.commit_sha,
        "branch": scan.branch,
        "scan_id": scan.id,
        "trigger": "pull_request",
        "pr_number": scan.pr_number,
    })

    return {"status": "pipeline_queued", "scan_id": scan.id}


# ═══════════════════════════════════════════════════════════════════
# Repositories
# ═══════════════════════════════════════════════════════════════════


@api_router.get("/repositories", tags=["repositories"])
async def list_repositories(
    db: AsyncSession = Depends(get_db),
) -> list[RepositoryResponse]:
    """List all tracked repositories."""
    result = await db.execute(select(Repository).order_by(Repository.created_at.desc()))
    repos = result.scalars().all()
    return [RepositoryResponse.model_validate(r) for r in repos]


@api_router.post("/repositories", tags=["repositories"])
async def add_repository(
    data: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    """Register a new repository for tracking."""
    from app.integrations.github_client import get_github_client

    gh = get_github_client()
    repo_data = await gh.get_repository(data.full_name)

    repo = Repository(
        github_id=repo_data["id"],
        full_name=repo_data["full_name"],
        name=repo_data["name"],
        owner=repo_data["owner"]["login"],
        default_branch=repo_data.get("default_branch", "main"),
        clone_url=repo_data["clone_url"],
        description=repo_data.get("description"),
        language=repo_data.get("language"),
    )
    db.add(repo)
    await db.flush()

    logger.info("Repository added", repo=data.full_name)
    return RepositoryResponse.model_validate(repo)


@api_router.get("/repositories/{repo_id}", tags=["repositories"])
async def get_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    """Get repository details."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return RepositoryResponse.model_validate(repo)


# ═══════════════════════════════════════════════════════════════════
# Scans
# ═══════════════════════════════════════════════════════════════════


@api_router.get("/scans", tags=["scans"])
async def list_scans(
    repository_id: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    """List scans with optional filters."""
    query = select(Scan).order_by(Scan.created_at.desc())

    if repository_id:
        query = query.where(Scan.repository_id == repository_id)
    if status:
        query = query.where(Scan.status == status)

    # Count total
    count_query = select(func.count(Scan.id))
    if repository_id:
        count_query = count_query.where(Scan.repository_id == repository_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    scans = result.scalars().all()

    return PaginatedResponse(
        items=[ScanSummary.model_validate(s) for s in scans],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@api_router.post("/scans", tags=["scans"])
async def trigger_scan(
    data: ScanCreate,
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """Manually trigger a security scan."""
    result = await db.execute(
        select(Repository).where(Repository.id == data.repository_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    scan = Scan(
        repository_id=repo.id,
        commit_sha=data.commit_sha or "HEAD",
        branch=data.branch or repo.default_branch,
        trigger=ScanTrigger.MANUAL,
        status=ScanStatus.QUEUED,
    )
    db.add(scan)
    await db.flush()

    from app.tasks.celery_app import run_pipeline
    run_pipeline.delay(scan.id, {
        "repository_id": repo.id,
        "repository_full_name": repo.full_name,
        "commit_sha": scan.commit_sha,
        "branch": scan.branch,
        "scan_id": scan.id,
        "trigger": "manual",
    })

    return ScanResponse.model_validate(scan)


@api_router.get("/scans/{scan_id}", tags=["scans"])
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """Get scan details."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse.model_validate(scan)


# ═══════════════════════════════════════════════════════════════════
# Findings
# ═══════════════════════════════════════════════════════════════════


@api_router.get("/scans/{scan_id}/findings", tags=["findings"])
async def list_findings(
    scan_id: str,
    severity: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[FindingResponse]:
    """List findings for a scan."""
    query = select(Finding).where(Finding.scan_id == scan_id)
    if severity:
        query = query.where(Finding.severity == severity)
    query = query.order_by(Finding.severity, Finding.created_at)
    result = await db.execute(query)
    findings = result.scalars().all()
    return [FindingResponse.model_validate(f) for f in findings]


@api_router.get("/findings", tags=["findings"])
async def list_all_findings(
    severity: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    """List findings across all scans."""
    query = select(Finding).order_by(Finding.created_at.desc())
    count_query = select(func.count(Finding.id))
    if severity:
        query = query.where(Finding.severity == severity)
        count_query = count_query.where(Finding.severity == severity)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    findings = result.scalars().all()
    return PaginatedResponse(
        items=[FindingResponse.model_validate(f) for f in findings],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


# ═══════════════════════════════════════════════════════════════════
# Agents
# ═══════════════════════════════════════════════════════════════════


@api_router.get("/agents", tags=["agents"])
async def list_agents() -> list[dict]:
    """List all registered security agents."""
    from app.agents.registry import get_agent_registry
    registry = get_agent_registry()
    return registry.list_agents()


@api_router.get("/agents/{agent_name}/runs", tags=["agents"])
async def get_agent_runs(
    agent_name: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get recent runs for a specific agent."""
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.agent_name == agent_name)
        .order_by(AgentRun.created_at.desc())
        .limit(20)
    )
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "scan_id": r.scan_id,
            "status": r.status,
            "confidence": r.confidence_score,
            "findings_count": r.findings_count,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


# ═══════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════


@api_router.get("/dashboard", tags=["dashboard"])
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get dashboard overview data."""
    # Repository count
    repo_count = await db.execute(select(func.count(Repository.id)))
    total_repos = repo_count.scalar() or 0

    # Active scans
    active_result = await db.execute(
        select(func.count(Scan.id)).where(
            Scan.status.in_([
                ScanStatus.QUEUED.value,
                ScanStatus.INDEXING.value,
                ScanStatus.SCANNING.value,
            ])
        )
    )
    active_scans = active_result.scalar() or 0

    # Finding counts
    finding_counts = await db.execute(
        select(Finding.severity, func.count(Finding.id))
        .group_by(Finding.severity)
    )
    severity_dist = dict(finding_counts.all())

    total_findings = sum(severity_dist.values())

    # Recent scans
    recent_result = await db.execute(
        select(Scan).order_by(Scan.created_at.desc()).limit(10)
    )
    recent_scans = [
        ScanSummary.model_validate(s).model_dump()
        for s in recent_result.scalars().all()
    ]

    # Average security score
    avg_result = await db.execute(
        select(func.avg(Scan.security_score)).where(
            Scan.status == ScanStatus.COMPLETED.value
        )
    )
    avg_score = avg_result.scalar() or 100

    # Patch/test counts
    patch_result = await db.execute(select(func.count(Patch.id)))
    total_patches = patch_result.scalar() or 0

    return {
        "total_repositories": total_repos,
        "active_scans": active_scans,
        "total_findings": total_findings,
        "critical_findings": severity_dist.get("critical", 0),
        "average_security_score": round(float(avg_score), 1),
        "patches_generated": total_patches,
        "tests_generated": 0,
        "recent_scans": recent_scans,
        "severity_distribution": severity_dist,
    }


# ═══════════════════════════════════════════════════════════════════
# Knowledge Graph
# ═══════════════════════════════════════════════════════════════════


@api_router.get("/graph/{repo_id}", tags=["knowledge-graph"])
async def get_knowledge_graph(
    repo_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get knowledge graph visualization data for a repository."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    kg = request.app.state.knowledge_graph
    if not kg:
        return {"nodes": [], "edges": [], "message": "Knowledge graph not available"}

    return await kg.get_graph_visualization(repo.full_name)


# ═══════════════════════════════════════════════════════════════════
# RAG
# ═══════════════════════════════════════════════════════════════════


@api_router.get("/knowledge/search", tags=["knowledge"])
async def search_knowledge(
    query: str = Query(..., min_length=3),
    request: Request = None,
) -> list[dict]:
    """Search the security knowledge base."""
    rag = request.app.state.rag
    if not rag:
        return []

    results = await rag.search(query, top_k=10)
    return results


@api_router.get("/knowledge/stats", tags=["knowledge"])
async def knowledge_stats(request: Request) -> dict:
    """Get knowledge base collection statistics."""
    rag = request.app.state.rag
    if not rag:
        return {"status": "unavailable"}
    return await rag.get_collection_stats()


# ═══════════════════════════════════════════════════════════════════
# Digital Twin
# ═══════════════════════════════════════════════════════════════════


@api_router.get("/digital-twin/{repo_id}", tags=["digital-twin"])
async def get_digital_twin(
    repo_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get the full Digital Twin graph for a repository.

    Returns all nodes and edges for Cytoscape.js visualization.
    """
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    kg = request.app.state.knowledge_graph
    if not kg:
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    from app.knowledge.digital_twin import get_digital_twin_service
    twin = get_digital_twin_service(kg)
    return await twin.get_digital_twin(repo.full_name)


@api_router.get("/digital-twin/{repo_id}/node/{node_id}", tags=["digital-twin"])
async def get_digital_twin_node(
    repo_id: str,
    node_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single Digital Twin node with its direct neighbors."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    kg = request.app.state.knowledge_graph
    if not kg:
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    from app.knowledge.digital_twin import get_digital_twin_service
    twin = get_digital_twin_service(kg)
    node_detail = await twin.get_node_detail(node_id)
    if not node_detail:
        raise HTTPException(status_code=404, detail="Node not found")
    return node_detail


@api_router.get("/digital-twin/{repo_id}/stats", tags=["digital-twin"])
async def get_digital_twin_stats(
    repo_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get node/edge count statistics for a Digital Twin."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    kg = request.app.state.knowledge_graph
    if not kg:
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    from app.knowledge.digital_twin import get_digital_twin_service
    twin = get_digital_twin_service(kg)
    data = await twin.get_digital_twin(repo.full_name)
    return data.get("stats", {})


@api_router.get("/digital-twin/{repo_id}/search", tags=["digital-twin"])
async def search_digital_twin(
    repo_id: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=200),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Full-text search over Digital Twin node labels/names."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    kg = request.app.state.knowledge_graph
    if not kg:
        raise HTTPException(status_code=503, detail="Knowledge graph not available")

    from app.knowledge.digital_twin import get_digital_twin_service
    twin = get_digital_twin_service(kg)
    nodes = await twin.search_nodes(repo.full_name, q, limit=limit)
    return {"nodes": nodes, "total": len(nodes)}


# ═══════════════════════════════════════════════════════════════════
# GitHub Events
# ═══════════════════════════════════════════════════════════════════


@api_router.get("/events", tags=["events"])
async def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all GitHub events (paginated, most recent first)."""
    offset = (page - 1) * page_size
    total_result = await db.execute(select(func.count(GitHubEvent.id)))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(GitHubEvent)
        .order_by(desc(GitHubEvent.created_at))
        .offset(offset)
        .limit(page_size)
    )
    events = result.scalars().all()

    return {
        "items": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "action": e.action,
                "repository_id": e.repository_id,
                "sender": e.sender,
                "commit_sha": e.commit_sha,
                "branch": e.branch,
                "pr_number": e.pr_number,
                "processing_status": e.processing_status,
                "twin_nodes_created": e.twin_nodes_created,
                "twin_nodes_updated": e.twin_nodes_updated,
                "twin_edges_created": e.twin_edges_created,
                "created_at": str(e.created_at),
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@api_router.get("/events/{repo_id}", tags=["events"])
async def list_repo_events(
    repo_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List GitHub events for a specific repository."""
    query = select(GitHubEvent).where(GitHubEvent.repository_id == repo_id)
    if event_type:
        query = query.where(GitHubEvent.event_type == event_type)

    count_q = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(desc(GitHubEvent.created_at))
        .offset(offset)
        .limit(page_size)
    )
    events = result.scalars().all()

    return {
        "items": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "action": e.action,
                "sender": e.sender,
                "commit_sha": e.commit_sha,
                "branch": e.branch,
                "pr_number": e.pr_number,
                "processing_status": e.processing_status,
                "twin_nodes_created": e.twin_nodes_created,
                "twin_nodes_updated": e.twin_nodes_updated,
                "created_at": str(e.created_at),
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# ═══════════════════════════════════════════════════════════════════
# Threat Evolution
# ═══════════════════════════════════════════════════════════════════


@api_router.get(
    "/threat-evolution/{repo_full_name:path}/timelines",
    response_model=list[ThreatTimelineSummary],
    tags=["threat-evolution"],
)
async def list_threat_timelines(repo_full_name: str):
    """List all threat evolution timelines for a repository."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.threat_evolution import ThreatEvolutionEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = ThreatEvolutionEngine(kg._driver)
        timelines = await engine.get_all_timelines(repo_full_name)
        await kg.close()
        return timelines
    except Exception as exc:
        logger.error("Failed to list threat timelines", error=str(exc))
        raise HTTPException(500, f"Failed to load timelines: {exc}")


@api_router.get(
    "/threat-evolution/{repo_full_name:path}/timeline/{threat_id}",
    response_model=ThreatTimelineResponse,
    tags=["threat-evolution"],
)
async def get_threat_timeline(repo_full_name: str, threat_id: str):
    """Get the full evolution timeline for a specific threat."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.threat_evolution import ThreatEvolutionEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = ThreatEvolutionEngine(kg._driver)
        timeline = await engine.get_evolution_timeline(repo_full_name, threat_id)
        await kg.close()
        return timeline
    except Exception as exc:
        logger.error("Failed to get threat timeline", error=str(exc))
        raise HTTPException(500, f"Failed to load timeline: {exc}")


@api_router.get(
    "/threat-evolution/prediction/{threat_id}",
    response_model=ThreatTrajectoryResponse | None,
    tags=["threat-evolution"],
)
async def get_threat_prediction(threat_id: str):
    """Get the latest LLM-predicted trajectory for a threat."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.threat_evolution import ThreatEvolutionEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = ThreatEvolutionEngine(kg._driver)
        prediction = await engine.get_latest_prediction(threat_id)
        await kg.close()
        if not prediction:
            raise HTTPException(404, "No prediction found for this threat")
        return prediction
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get prediction", error=str(exc))
        raise HTTPException(500, f"Failed to load prediction: {exc}")


@api_router.get(
    "/threat-evolution/{repo_full_name:path}/exploitability",
    response_model=list[ExploitabilityRankingResponse],
    tags=["threat-evolution"],
)
async def get_exploitability_rankings(
    repo_full_name: str,
    top_n: int = Query(default=20, le=100),
):
    """Rank threats by exploitability urgency score."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.threat_evolution import ThreatEvolutionEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = ThreatEvolutionEngine(kg._driver)
        rankings = await engine.get_exploitability_rankings(repo_full_name, top_n)
        await kg.close()
        return rankings
    except Exception as exc:
        logger.error("Failed to get exploitability rankings", error=str(exc))
        raise HTTPException(500, f"Failed to load rankings: {exc}")


# ═══════════════════════════════════════════════════════════════════
# Attack Chain
# ═══════════════════════════════════════════════════════════════════


@api_router.get(
    "/attack-chains/{repo_full_name:path}/discover",
    response_model=list[AttackChainResponse],
    tags=["attack-chain"],
)
async def discover_attack_chains(
    repo_full_name: str,
    max_depth: int = Query(default=6, le=10),
    limit: int = Query(default=20, le=50),
):
    """Discover attack chains by traversing the knowledge graph."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.attack_chain import AttackChainEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = AttackChainEngine(kg._driver)
        chains = await engine.discover_chains(repo_full_name, max_depth, limit)
        # Persist discovered chains
        for chain in chains:
            await engine.persist_chain(chain)
        await kg.close()
        return chains
    except Exception as exc:
        logger.error("Failed to discover attack chains", error=str(exc))
        raise HTTPException(500, f"Chain discovery failed: {exc}")


@api_router.get(
    "/attack-chains/{repo_full_name:path}/list",
    response_model=list[AttackChainResponse],
    tags=["attack-chain"],
)
async def list_attack_chains(
    repo_full_name: str,
    limit: int = Query(default=50, le=100),
):
    """List previously discovered attack chains."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.attack_chain import AttackChainEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = AttackChainEngine(kg._driver)
        chains = await engine.get_persisted_chains(repo_full_name, limit)
        await kg.close()
        return chains
    except Exception as exc:
        logger.error("Failed to list attack chains", error=str(exc))
        raise HTTPException(500, f"Failed to load chains: {exc}")


@api_router.post(
    "/attack-chains/movie",
    response_model=AttackMovieResponse,
    tags=["attack-chain"],
)
async def get_attack_movie(chain: AttackChainResponse):
    """Generate a cinematic attack movie from a chain."""
    from app.knowledge.attack_chain import AttackChainEngine

    try:
        engine = AttackChainEngine(None)  # No driver needed for movie gen
        movie = await engine.build_attack_movie(chain.model_dump())
        return movie
    except Exception as exc:
        logger.error("Failed to build attack movie", error=str(exc))
        raise HTTPException(500, f"Movie generation failed: {exc}")


@api_router.get(
    "/attack-chains/{repo_full_name:path}/blast-radius/{node_id}",
    response_model=BlastRadiusResponse,
    tags=["attack-chain"],
)
async def get_blast_radius(
    repo_full_name: str,
    node_id: str,
    max_depth: int = Query(default=4, le=8),
):
    """Compute blast radius from a compromised node."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.attack_chain import AttackChainEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = AttackChainEngine(kg._driver)
        radius = await engine.get_blast_radius(repo_full_name, node_id, max_depth)
        await kg.close()
        return radius
    except Exception as exc:
        logger.error("Failed to compute blast radius", error=str(exc))
        raise HTTPException(500, f"Blast radius failed: {exc}")


# ═══════════════════════════════════════════════════════════════════
# Business Impact
# ═══════════════════════════════════════════════════════════════════


@api_router.post(
    "/business-impact/{repo_full_name:path}",
    response_model=BusinessImpactResponse,
    tags=["business-impact"],
)
async def compute_business_impact(
    repo_full_name: str,
    body: BusinessImpactRequest | None = None,
):
    """Compute dollar-value business impact assessment."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.business_impact import BusinessImpactEngine

    params = body or BusinessImpactRequest()
    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = BusinessImpactEngine(kg._driver)
        result = await engine.compute_repository_impact(
            repo_full_name=repo_full_name,
            annual_revenue=params.annual_revenue,
            industry=params.industry,
            estimated_records=params.estimated_records,
            compliance_frameworks=params.compliance_frameworks,
        )
        await kg.close()
        return result
    except Exception as exc:
        logger.error("Business impact computation failed", error=str(exc))
        raise HTTPException(500, f"Impact computation failed: {exc}")


# ═══════════════════════════════════════════════════════════════════
# Security Timeline
# ═══════════════════════════════════════════════════════════════════


@api_router.post(
    "/security-timeline/{repo_full_name:path}/snapshot",
    response_model=TimelineSnapshotDetail,
    tags=["security-timeline"],
)
async def capture_security_snapshot(
    repo_full_name: str,
    trigger: str = Query(default="manual"),
):
    """Capture a point-in-time security snapshot."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.security_timeline import SecurityTimelineEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = SecurityTimelineEngine(kg._driver)
        snapshot = await engine.capture_snapshot(repo_full_name, trigger)
        await kg.close()
        return snapshot
    except Exception as exc:
        logger.error("Snapshot capture failed", error=str(exc))
        raise HTTPException(500, f"Snapshot failed: {exc}")


@api_router.get(
    "/security-timeline/{repo_full_name:path}/snapshots",
    response_model=list[TimelineSnapshotSummary],
    tags=["security-timeline"],
)
async def get_security_timeline(
    repo_full_name: str,
    limit: int = Query(default=50, le=200),
    since: str | None = Query(default=None),
):
    """Get ordered timeline of security snapshots."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.security_timeline import SecurityTimelineEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = SecurityTimelineEngine(kg._driver)
        timeline = await engine.get_timeline(repo_full_name, limit, since)
        await kg.close()
        return timeline
    except Exception as exc:
        logger.error("Timeline query failed", error=str(exc))
        raise HTTPException(500, f"Timeline failed: {exc}")


@api_router.get(
    "/security-timeline/diff/{snapshot_a}/{snapshot_b}",
    response_model=TimelineDiffResponse,
    tags=["security-timeline"],
)
async def diff_security_snapshots(snapshot_a: str, snapshot_b: str):
    """Compare two snapshots and return the delta."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.security_timeline import SecurityTimelineEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = SecurityTimelineEngine(kg._driver)
        diff = await engine.diff_snapshots(snapshot_a, snapshot_b)
        await kg.close()
        if "error" in diff:
            raise HTTPException(404, diff["error"])
        return diff
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Snapshot diff failed", error=str(exc))
        raise HTTPException(500, f"Diff failed: {exc}")


@api_router.get(
    "/security-timeline/{repo_full_name:path}/trend",
    response_model=PostureTrendResponse,
    tags=["security-timeline"],
)
async def get_posture_trend(
    repo_full_name: str,
    days: int = Query(default=30, le=365),
):
    """Get security posture trend over time."""
    from app.knowledge.graph import KnowledgeGraphService
    from app.knowledge.security_timeline import SecurityTimelineEngine

    try:
        kg = KnowledgeGraphService()
        await kg.initialize()
        engine = SecurityTimelineEngine(kg._driver)
        trend = await engine.get_posture_trend(repo_full_name, days)
        await kg.close()
        return trend
    except Exception as exc:
        logger.error("Posture trend failed", error=str(exc))
        raise HTTPException(500, f"Trend failed: {exc}")


# ═══════════════════════════════════════════════════════════════════
# WebSocket — Digital Twin Live Updates
# ═══════════════════════════════════════════════════════════════════


@api_router.websocket("/ws/digital-twin/{repo_id}")
async def digital_twin_websocket(ws: WebSocket, repo_id: str) -> None:
    """WebSocket endpoint for live Digital Twin graph updates."""
    from app.api.websocket import digital_twin_ws_handler
    await digital_twin_ws_handler(ws, repo_id)
