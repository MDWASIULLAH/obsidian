"""GitHub App onboarding and repository discovery."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.integrations.github_client import get_github_client
from app.models.database import get_db
from app.models.github_installation import GitHubInstallation
from app.models.repository import Repository
from app.models.user import User

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


class InstallUrlRequest(BaseModel):
    user_id: str | None = None


class SyncInstallationPayload(BaseModel):
    installation_id: int
    user_id: str | None = None


async def _get_user(db: AsyncSession, user_id: str | None) -> User | None:
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


@router.post("/github-app/install-url")
async def get_github_app_install_url(payload: InstallUrlRequest):
    """Return the GitHub App installation URL for the configured OBSIDIAN app."""
    settings = get_settings()
    if not settings.github_app_slug:
        raise HTTPException(
            status_code=400,
            detail="GITHUB_APP_SLUG is required to install the GitHub App",
        )

    params = {}
    if payload.user_id:
        params["state"] = payload.user_id

    query = f"?{urlencode(params)}" if params else ""
    return {
        "install_url": f"https://github.com/apps/{settings.github_app_slug}/installations/new{query}",
        "setup_url": f"{settings.frontend_url.rstrip('/')}/dashboard/setup",
    }


@router.post("/github-app/sync-installation")
async def sync_github_app_installation(
    payload: SyncInstallationPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Persist a GitHub App installation and import all authorized repositories.

    This is called after GitHub redirects back with `installation_id`.
    """
    gh = get_github_client()
    user = await _get_user(db, payload.user_id)

    try:
        installation = await gh.get_installation(payload.installation_id)
        repositories = await gh.list_installation_repositories(payload.installation_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to sync GitHub App installation: {exc}",
        ) from exc

    account = installation.get("account") or {}
    account_login = account.get("login") or "unknown"
    account_type = account.get("type") or "User"

    result = await db.execute(
        select(GitHubInstallation).where(
            GitHubInstallation.installation_id == payload.installation_id
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        record = GitHubInstallation(installation_id=payload.installation_id)
        db.add(record)

    record.user_id = user.id if user else None
    record.account_login = account_login
    record.account_type = account_type
    record.target_type = installation.get("target_type")
    record.repository_selection = installation.get("repository_selection") or "selected"
    record.permissions = installation.get("permissions") or {}
    record.events = installation.get("events") or []
    record.is_active = True

    imported = 0
    updated = 0
    for repo_data in repositories:
        full_name = repo_data.get("full_name")
        if not full_name:
            continue

        repo_result = await db.execute(
            select(Repository).where(Repository.github_id == repo_data.get("id", 0))
        )
        repo = repo_result.scalar_one_or_none()
        if repo is None:
            repo = Repository(github_id=repo_data.get("id", 0), full_name=full_name)
            db.add(repo)
            imported += 1
        else:
            updated += 1

        owner = repo_data.get("owner") or {}
        repo.full_name = full_name
        repo.name = repo_data.get("name") or full_name.rsplit("/", 1)[-1]
        repo.owner = owner.get("login") or full_name.split("/", 1)[0]
        repo.default_branch = repo_data.get("default_branch") or "main"
        repo.clone_url = repo_data.get("clone_url") or ""
        repo.description = repo_data.get("description")
        repo.language = repo_data.get("language")
        repo.installation_id = payload.installation_id
        repo.user_id = user.id if user else None
        repo.is_active = True

    await db.commit()

    return {
        "status": "synced",
        "installation_id": payload.installation_id,
        "account": account_login,
        "repository_selection": record.repository_selection,
        "repositories_authorized": len(repositories),
        "repositories_imported": imported,
        "repositories_updated": updated,
    }


@router.get("/github-app/status")
async def github_app_status(user_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """Return the current user's active GitHub App installations."""
    query = select(GitHubInstallation).where(GitHubInstallation.is_active.is_(True))
    if user_id:
        query = query.where(GitHubInstallation.user_id == user_id)
    result = await db.execute(query)
    installs = result.scalars().all()
    return [
        {
            "installation_id": install.installation_id,
            "account_login": install.account_login,
            "account_type": install.account_type,
            "repository_selection": install.repository_selection,
            "events": install.events,
            "created_at": install.created_at,
        }
        for install in installs
    ]
