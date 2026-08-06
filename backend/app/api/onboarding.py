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
        
        # 2. Upload the GitHub Actions Workflow (The 24/7 Engine trigger)
        workflow_content = """name: OBSIDIAN Security Multiplex

on:
  schedule:
    - cron: '*/5 * * * *' # Runs every 5 minutes (24/7 loop)
  workflow_dispatch:

jobs:
  multiplex-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install Dependencies
        run: pip install httpx
        
      - name: Execute Autonomous Multiplex Agent
        run: python agent.py
        env:
          OBSIDIAN_API_URL: "https://your-saas-url.com/api/v1" # To be replaced with production URL
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""
        encoded_workflow = base64.b64encode(workflow_content.encode("utf-8")).decode("utf-8")
        workflow_url = f"https://api.github.com/repos/{user.username}/{repo_name}/contents/.github/workflows/sentinel-multiplex.yml"
        
        await client.put(workflow_url, headers=headers, json={
            "message": "Initialize OBSIDIAN 24/7 Workflow Engine",
            "content": encoded_workflow
        })

        # 3. Upload the Autonomous Agent File (agent.py)
        agent_content = """import os
import time
import httpx
import datetime

API_URL = os.environ.get("OBSIDIAN_API_URL", "http://localhost:8000/api/v1")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

def run_multiplex():
    print("Starting OBSIDIAN Autonomous Security Multiplex (Robust Engine)...")
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Fetch real repositories
    repos_url = "https://api.github.com/user/repos?per_page=10&affiliation=owner"
    try:
        repos_res = httpx.get(repos_url, headers=headers)
        repos = repos_res.json()
    except Exception as e:
        print("Failed to fetch repos:", e)
        return

    findings = []
    
    # 2. Perform real basic heuristic scan on repos (e.g. checking for default branch protection or secrets)
    for repo in repos:
        repo_name = repo.get("full_name")
        print(f"Scanning {repo_name}...")
        
        # Check 1: Private repo visibility
        if not repo.get("private"):
            findings.append({
                "severity": "high", 
                "title": f"Repository {repo_name} is public. Consider making it private.",
                "repo": repo_name
            })
            
        # Check 2: Branch protection (requires admin access, simulation fallback if 403)
        default_branch = repo.get("default_branch", "main")
        branch_url = f"https://api.github.com/repos/{repo_name}/branches/{default_branch}/protection"
        bp_res = httpx.get(branch_url, headers=headers)
        if bp_res.status_code == 404:
            findings.append({
                "severity": "medium",
                "title": f"No branch protection rules on {default_branch} for {repo_name}",
                "repo": repo_name
            })
            
        time.sleep(1) # rate limit prevention

    if not findings:
        findings.append({
            "severity": "info",
            "title": "All initial heuristic checks passed across repositories.",
            "repo": "system"
        })

    # 3. Beam the live tracking details back to the SaaS Dashboard
    for finding in findings:
        payload = {
            "event_type": "live_scan_finding",
            "timestamp": datetime.datetime.now().isoformat(),
            "finding": {
                "severity": finding["severity"],
                "title": finding["title"]
            },
            "repo": finding.get("repo", "system")
        }
        
        print(f"Beaming finding to {API_URL}/webhooks/agent-sync...")
        try:
            res = httpx.post(f"{API_URL}/webhooks/agent-sync", json=payload, timeout=10.0)
            print("Sync complete:", res.status_code)
        except Exception as e:
            print("Failed to sync:", str(e))
            
        time.sleep(0.5)

if __name__ == "__main__":
    run_multiplex()
"""
        encoded_agent = base64.b64encode(agent_content.encode("utf-8")).decode("utf-8")
        agent_url = f"https://api.github.com/repos/{user.username}/{repo_name}/contents/agent.py"
        
        await client.put(agent_url, headers=headers, json={
            "message": "Initialize Autonomous Agent File",
            "content": encoded_agent
        })

    return {"status": "success", "message": "Security center provisioned successfully", "repo": repo_name}
