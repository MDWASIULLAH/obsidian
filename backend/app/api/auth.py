from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from pydantic import BaseModel

from app.models.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])

class AuthPayload(BaseModel):
    provider: str = "github"
    provider_account_id: str | None = None
    github_id: str | None = None
    google_id: str | None = None
    username: str
    email: str | None = None
    avatar_url: str | None = None
    access_token: str | None = None

@router.post("/sync")
async def sync_user(payload: AuthPayload, db: AsyncSession = Depends(get_db)):
    """Sync a NextAuth OAuth identity to the backend database."""
    provider = payload.provider.lower()
    provider_account_id = payload.provider_account_id or payload.github_id or payload.google_id
    if not provider_account_id:
        raise HTTPException(status_code=400, detail="provider_account_id is required")

    conditions = [
        (User.provider == provider) & (User.provider_account_id == provider_account_id),
    ]
    if payload.github_id:
        conditions.append(User.github_id == payload.github_id)
    if payload.google_id:
        conditions.append(User.google_id == payload.google_id)

    stmt = select(User).where(or_(*conditions))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        user.provider = provider
        user.provider_account_id = provider_account_id
        user.username = payload.username
        if payload.email:
            user.email = payload.email
        if payload.avatar_url:
            user.avatar_url = payload.avatar_url
        if payload.github_id:
            user.github_id = payload.github_id
        if payload.google_id:
            user.google_id = payload.google_id
        if provider == "github" and payload.access_token:
            user.github_token = payload.access_token
    else:
        user = User(
            provider=provider,
            provider_account_id=provider_account_id,
            github_id=payload.github_id if provider == "github" else None,
            google_id=payload.google_id if provider == "google" else None,
            username=payload.username,
            email=payload.email,
            avatar_url=payload.avatar_url,
            github_token=payload.access_token if provider == "github" else None,
        )
        db.add(user)
    
    await db.commit()
    await db.refresh(user)
    return {"status": "success", "user_id": user.id}

@router.get("/me")
async def get_me(user_id: str, db: AsyncSession = Depends(get_db)):
    """Mock auth extraction: ideally we'd pass a JWT in Authorization header."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar_url": user.avatar_url
    }

import httpx

@router.get("/github-stats")
async def get_github_stats(user_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch real repository stats from GitHub using the user's OAuth token."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.github_token:
        raise HTTPException(status_code=404, detail="User or GitHub token not found")

    async with httpx.AsyncClient() as client:
        # Fetch repos
        res = await client.get(
            "https://api.github.com/user/repos?per_page=100&affiliation=owner",
            headers={"Authorization": f"Bearer {user.github_token}", "Accept": "application/vnd.github.v3+json"}
        )
        if res.status_code != 200:
            return {"repo_count": 0, "error": "Failed to fetch from GitHub"}
        
        repos = res.json()
        return {
            "repo_count": len(repos),
            "username": user.username,
            "avatar_url": user.avatar_url
        }
