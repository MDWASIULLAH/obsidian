"""
SENTINEL AI X — Celery Application & Task Definitions.

Configures Celery with Redis as broker and defines the
main pipeline task that triggers the full LangGraph workflow.
"""

from __future__ import annotations

import asyncio

from celery import Celery

from app.config import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════════
# Celery Application
# ═══════════════════════════════════════════════════════════════════

celery_app = Celery(
    "sentinel",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.celery_app.run_pipeline": {"queue": "pipeline"},
        "app.tasks.celery_app.index_repository_task": {"queue": "indexing"},
        "app.tasks.celery_app.generate_report": {"queue": "default"},
        "app.tasks.celery_app.process_github_event": {"queue": "events"},
    },
    beat_schedule={
        "health-check": {
            "task": "app.tasks.celery_app.health_check",
            "schedule": 300.0,
        },
        "recompute-twin-scores": {
            "task": "app.tasks.celery_app.health_check",
            "schedule": 900.0,  # Every 15 minutes
        },
    },
)


# ═══════════════════════════════════════════════════════════════════
# Helper to run async in Celery
# ═══════════════════════════════════════════════════════════════════


def run_async(coro):
    """Run an async function inside a Celery sync task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ═══════════════════════════════════════════════════════════════════
# Tasks
# ═══════════════════════════════════════════════════════════════════


@celery_app.task(
    name="app.tasks.celery_app.run_pipeline",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def run_pipeline(self, scan_id: str, initial_state: dict) -> dict:
    """
    Main pipeline task — runs the full LangGraph security workflow.

    This is triggered by GitHub webhooks or manual API calls.
    The Celery worker invokes the async LangGraph pipeline.
    """
    from app.agents.orchestrator import run_security_pipeline
    from app.models.database import async_session_factory
    from app.models.scan import Scan, ScanStatus
    import structlog

    logger = structlog.get_logger()
    logger.info("Pipeline task started", scan_id=scan_id)

    try:
        # Update scan status to scanning
        async def update_status(status: ScanStatus):
            async with async_session_factory() as session:
                from sqlalchemy import update
                await session.execute(
                    update(Scan).where(Scan.id == scan_id).values(status=status.value)
                )
                await session.commit()

        run_async(update_status(ScanStatus.SCANNING))

        # Run the full pipeline
        final_state = run_async(run_security_pipeline(initial_state))

        # Persist results to database
        async def save_results(state: dict):
            async with async_session_factory() as session:
                from sqlalchemy import update
                severity_counts = {}
                for f in state.get("all_findings", []):
                    sev = f.get("severity", "info")
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1

                await session.execute(
                    update(Scan).where(Scan.id == scan_id).values(
                        status=ScanStatus.COMPLETED.value,
                        total_findings=len(state.get("all_findings", [])),
                        critical_count=severity_counts.get("critical", 0),
                        high_count=severity_counts.get("high", 0),
                        medium_count=severity_counts.get("medium", 0),
                        low_count=severity_counts.get("low", 0),
                        patches_generated=len(state.get("generated_patches", [])),
                        tests_generated=len(state.get("generated_tests", [])),
                        security_score=state.get("security_score", 0),
                        confidence=int(state.get("overall_confidence", 0) * 100),
                        threat_model=str(state.get("threat_model", {})),
                        pr_url=state.get("pr_url"),
                        duration_seconds=state.get("duration_seconds"),
                    )
                )
                await session.commit()

                # Save individual findings
                from app.models.finding import Finding
                for f in state.get("all_findings", []):
                    finding = Finding(
                        scan_id=scan_id,
                        title=f.get("title", ""),
                        description=f.get("description", ""),
                        severity=f.get("severity", "info"),
                        category=f.get("category", "vulnerability"),
                        confidence=f.get("confidence", 0.0),
                        file_path=f.get("file_path"),
                        line_start=f.get("line_start"),
                        line_end=f.get("line_end"),
                        code_snippet=f.get("code_snippet"),
                        cwe_id=f.get("cwe_id"),
                        cve_id=f.get("cve_id"),
                        owasp_category=f.get("owasp_category"),
                        mitre_technique=f.get("mitre_technique"),
                        agent_name=f.get("agent_name", ""),
                        reasoning=f.get("reasoning"),
                        recommendation=f.get("recommendation"),
                        citations=str(f.get("citations", [])),
                    )
                    session.add(finding)
                await session.commit()

        run_async(save_results(final_state))

        logger.info("Pipeline task completed", scan_id=scan_id)
        return {"status": "completed", "scan_id": scan_id}

    except Exception as e:
        logger.error("Pipeline task failed", scan_id=scan_id, error=str(e))

        async def mark_failed():
            async with async_session_factory() as session:
                from sqlalchemy import update
                await session.execute(
                    update(Scan).where(Scan.id == scan_id).values(
                        status=ScanStatus.FAILED.value,
                        error_message=str(e),
                    )
                )
                await session.commit()

        run_async(mark_failed())
        raise self.retry(exc=e)


@celery_app.task(name="app.tasks.celery_app.index_repository_task")
def index_repository_task(repo_full_name: str) -> dict:
    """Index a repository into the knowledge graph."""
    from app.knowledge.graph import KnowledgeGraphService
    import structlog

    logger = structlog.get_logger()
    logger.info("Indexing repository", repo=repo_full_name)

    async def do_index():
        kg = KnowledgeGraphService()
        await kg.initialize()
        try:
            await kg.index_repository(repo_full_name, [], {})
        finally:
            await kg.close()

    run_async(do_index())
    return {"status": "indexed", "repo": repo_full_name}


@celery_app.task(name="app.tasks.celery_app.generate_report")
def generate_report(scan_id: str) -> dict:
    """Generate a security report for a scan."""
    return {"status": "report_generated", "scan_id": scan_id}


@celery_app.task(name="app.tasks.celery_app.health_check")
def health_check() -> dict:
    """Periodic health check task."""
    return {"status": "healthy"}


# ═══════════════════════════════════════════════════════════════════
# GitHub Event Processing Task
# ═══════════════════════════════════════════════════════════════════


@celery_app.task(
    name="app.tasks.celery_app.process_github_event",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_github_event(
    self,
    event_id: str,
    repo_id: str,
    event_type: str,
    payload: dict,
    event_context: dict,
) -> dict:
    """
    Process a single GitHub webhook event asynchronously.

    Steps:
      1. Update the Digital Twin graph (always)
      2. Broadcast graph diff via WebSocket (if subscribers)
      3. Optionally trigger the full security pipeline
      4. Update the github_events record with processing stats
    """
    import structlog
    log = structlog.get_logger()
    log.info("Processing GitHub event", event_id=event_id, event_type=event_type)

    async def _process() -> dict:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import select, update
        from app.models.github_event import GitHubEvent, ProcessingStatus
        from app.knowledge.graph import KnowledgeGraphService
        from app.knowledge.digital_twin import get_digital_twin_service
        from app.api.websocket import broadcast_twin_update

        engine = create_async_engine(settings.database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        graph = KnowledgeGraphService()
        await graph.initialize()
        twin = get_digital_twin_service(graph)

        twin_stats: dict = {"nodes_created": 0, "nodes_updated": 0, "edges_created": 0}

        async with async_session() as db:
            # Mark as processing
            await db.execute(
                update(GitHubEvent)
                .where(GitHubEvent.id == event_id)
                .values(processing_status=ProcessingStatus.PROCESSING.value)
            )
            await db.commit()

            repo_full_name = payload.get("repository", {}).get("full_name", "")
            branch = event_context.get("branch") or ""
            commit_sha = event_context.get("commit_sha") or ""
            sender = event_context.get("sender", "unknown")
            changed_files = event_context.get("changed_files", [])
            action = event_context.get("action")

            try:
                # ── Digital Twin update ──────────────────────────
                if event_type == "push":
                    twin_stats = await twin.process_push_event(
                        repo_full_name=repo_full_name,
                        branch=branch,
                        commit_sha=commit_sha,
                        sender=sender,
                        changed_files=changed_files,
                        payload=payload,
                    )
                elif event_type in ("pull_request", "pull_request_review"):
                    pr = payload.get("pull_request", {})
                    twin_stats = await twin.process_pr_event(
                        repo_full_name=repo_full_name,
                        pr_number=event_context.get("pr_number") or 0,
                        head_sha=commit_sha,
                        head_branch=branch,
                        base_branch=pr.get("base", {}).get("ref", "main"),
                        action=action or "",
                        sender=sender,
                    )
                elif event_type in ("create", "delete") and event_context.get("ref_type") == "branch":
                    twin_stats = await twin.process_branch_event(
                        repo_full_name=repo_full_name,
                        branch=branch,
                        action="created" if event_type == "create" else "deleted",
                    )
                elif event_type in ("security_advisory", "dependabot_alert",
                                    "secret_scanning_alert", "code_scanning_alert"):
                    alert_key = "security_advisory" if event_type == "security_advisory" else "alert"
                    twin_stats = await twin.process_security_alert(
                        repo_full_name=repo_full_name,
                        event_type=event_type,
                        alert=payload.get(alert_key, {}),
                        action=action or "",
                    )
                elif event_type == "deployment":
                    twin_stats = await twin.process_deployment(
                        repo_full_name=repo_full_name,
                        deployment=payload.get("deployment", {}),
                        action=action or "",
                    )
                elif event_type == "workflow_run":
                    twin_stats = await twin.process_workflow_run(
                        repo_full_name=repo_full_name,
                        workflow_run=payload.get("workflow_run", {}),
                    )

                # ── Broadcast to WebSocket subscribers ───────────
                await broadcast_twin_update(
                    repo_id=repo_id,
                    event_type=event_type,
                    stats=twin_stats,
                )

                # ── Trigger security pipeline if required ─────────
                requires_pipeline = event_context.get("requires_full_pipeline", False)
                scan_id = None

                if requires_pipeline and repo_full_name:
                    from sqlalchemy import select as sa_select
                    from app.models.repository import Repository
                    from app.models.scan import Scan, ScanStatus, ScanTrigger

                    result = await db.execute(
                        sa_select(Repository).where(Repository.id == repo_id)
                    )
                    repo = result.scalar_one_or_none()
                    if repo:
                        if event_type == "push":
                            trigger = ScanTrigger.PUSH
                        elif event_type == "pull_request":
                            trigger = ScanTrigger.PULL_REQUEST
                        else:
                            trigger = ScanTrigger.MANUAL

                        scan = Scan(
                            repository_id=repo.id,
                            commit_sha=commit_sha or "",
                            branch=branch or repo.default_branch,
                            trigger=trigger,
                            status=ScanStatus.QUEUED,
                            pr_number=event_context.get("pr_number"),
                        )
                        db.add(scan)
                        await db.flush()
                        scan_id = scan.id

                        initial_state = {
                            "repository_id": repo.id,
                            "repository_full_name": repo_full_name,
                            "commit_sha": commit_sha,
                            "branch": branch,
                            "scan_id": scan.id,
                            "event_type": event_type,
                            "event_action": action,
                            "event_data": event_context,
                            "requires_full_pipeline": True,
                            "requested_agents": event_context.get("agent_routing_hints", []),
                            "changed_files": changed_files,
                        }
                        run_pipeline.delay(scan.id, initial_state)

                # ── Update event record ───────────────────────────
                await db.execute(
                    update(GitHubEvent)
                    .where(GitHubEvent.id == event_id)
                    .values(
                        processing_status=ProcessingStatus.COMPLETED.value,
                        twin_nodes_created=twin_stats.get("nodes_created", 0),
                        twin_nodes_updated=twin_stats.get("nodes_updated", 0),
                        twin_edges_created=twin_stats.get("edges_created", 0),
                        scan_id=scan_id,
                    )
                )
                await db.commit()

            except Exception as exc:
                log.error("Event processing failed", event_id=event_id, error=str(exc))
                await db.execute(
                    update(GitHubEvent)
                    .where(GitHubEvent.id == event_id)
                    .values(
                        processing_status=ProcessingStatus.FAILED.value,
                        processing_error=str(exc)[:1000],
                    )
                )
                await db.commit()
                raise

        await graph.close()
        return {"status": "processed", "event_id": event_id, "twin_stats": twin_stats}

    try:
        return run_async(_process())
    except Exception as exc:
        raise self.retry(exc=exc)
