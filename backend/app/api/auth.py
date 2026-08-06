from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.models.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])

class AuthPayload(BaseModel):
    github_id: str
    username: str
    email: str | None = None
    avatar_url: str | None = None
    access_token: str | None = None

@router.post("/sync")
async def sync_user(payload: AuthPayload, db: AsyncSession = Depends(get_db)):
    """Sync NextAuth GitHub session to the backend database."""
    # Find existing user
    stmt = select(User).where(User.github_id == payload.github_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        user.username = payload.username
        if payload.email:
            user.email = payload.email
        if payload.avatar_url:
            user.avatar_url = payload.avatar_url
        if payload.access_token:
            user.github_token = payload.access_token
    else:
        # Create new user
        user = User(
            github_id=payload.github_id,
            username=payload.username,
            email=payload.email,
            avatar_url=payload.avatar_url,
            github_token=payload.access_token
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
