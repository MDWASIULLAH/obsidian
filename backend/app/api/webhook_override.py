"""Production webhook path for push/PR scans without requiring a Celery worker."""

from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.live_scan import trigger_real_scan
from app.models.database import get_db
from app.models.repository import Repository
from app.models.schemas import ScanCreate

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/github")
async def github_webhook_override(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a real scan for push/PR events even when no Celery worker is running."""
    from app.integrations.github_client import get_github_client

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")
    client = get_github_client()

    if not client.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = json.loads(body or b"{}")
    repo_data = payload.get("repository", {})
    full_name = repo_data.get("full_name")

    if event_type == "ping":
        return {"status": "acknowledged", "event": event_type}

    if event_type not in {"push", "pull_request"} or not full_name:
        # Leave non-scan lifecycle/alert events to the existing event system.
        return {"status": "accepted", "event": event_type, "scan_triggered": False}

    if event_type == "pull_request" and payload.get("action") not in {"opened", "synchronize"}:
        return {"status": "ignored", "event": event_type, "action": payload.get("action")}

    result = await db.execute(select(Repository).where(Repository.full_name == full_name))
    repo = result.scalar_one_or_none()
    if not repo:
        repo = Repository(
            github_id=repo_data.get("id", 0),
            full_name=full_name,
            name=repo_data.get("name", full_name.split("/", 1)[-1]),
            owner=repo_data.get("owner", {}).get("login", full_name.split("/", 1)[0]),
            default_branch=repo_data.get("default_branch", "main"),
            clone_url=repo_data.get("clone_url", ""),
            description=repo_data.get("description"),
            language=repo_data.get("language"),
        )
        db.add(repo)
        await db.flush()

    if event_type == "push":
        commit_sha = payload.get("after") or repo.default_branch
        branch = payload.get("ref", "").replace("refs/heads/", "") or repo.default_branch
    else:
        pr = payload.get("pull_request", {})
        commit_sha = pr.get("head", {}).get("sha") or repo.default_branch
        branch = pr.get("head", {}).get("ref") or repo.default_branch

    await db.commit()
    result = await trigger_real_scan(
        ScanCreate(repository_id=repo.id, commit_sha=commit_sha, branch=branch),
        background_tasks,
        db,
    )
    return {
        "status": "accepted",
        "event": event_type,
        "scan_triggered": True,
        "scan_id": result.id,
        "repository": full_name,
    }
