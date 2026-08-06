import json
import base64
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.models.database import get_db
from app.models.user import User

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

class OnboardingPayload(BaseModel):
    user_id: str

@router.post("/provision-security-center")
async def provision_security_center(payload: OnboardingPayload, db: AsyncSession = Depends(get_db)):
    """
    Creates the central 'obsidian-security-center' repository on the user's GitHub
    and commits the initial multiplex agent configuration.
    """
    stmt = select(User).where(User.id == payload.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.github_token:
        raise HTTPException(status_code=400, detail="User or GitHub token not found")

    token = user.github_token
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    async with httpx.AsyncClient() as client:
        # 1. Create Repository
        repo_name = "obsidian-security-center"
        create_repo_url = "https://api.github.com/user/repos"
        repo_data = {
            "name": repo_name,
            "description": "OBSIDIAN Autonomous Security Multiplex - Central Command",
            "private": True,
            "auto_init": True
        }
        
        repo_res = await client.post(create_repo_url, headers=headers, json=repo_data)
        
        if repo_res.status_code not in (201, 422): # 422 usually means it already exists
            raise HTTPException(status_code=500, detail=f"Failed to create repo: {repo_res.text}")
        
        # 2. Upload multiplex-agent.yml configuration
        config_content = """# OBSIDIAN Security Multiplex Configuration
version: 1.0
agents:
  sast:
    enabled: true
    mode: aggressive
  dast:
    enabled: false
  secret_scanner:
    enabled: true
    
thresholds:
  critical: block_pr
  high: require_review
"""
        encoded_content = base64.b64encode(config_content.encode("utf-8")).decode("utf-8")
        
        file_url = f"https://api.github.com/repos/{user.username}/{repo_name}/contents/multiplex-agent.yml"
        
        # Check if file exists first to get sha (in case it already exists)
        file_check = await client.get(file_url, headers=headers)
        file_data = {
            "message": "Initialize OBSIDIAN Security Multiplex agent configuration",
            "content": encoded_content
        }
        if file_check.status_code == 200:
            file_data["sha"] = file_check.json()["sha"]
            
        file_res = await client.put(file_url, headers=headers, json=file_data)
        
        if file_res.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Failed to create config file: {file_res.text}")

    return {"status": "success", "message": "Security center provisioned successfully", "repo": repo_name}
