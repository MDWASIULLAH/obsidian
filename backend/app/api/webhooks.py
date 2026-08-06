from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from app.api.websocket import twin_ws_manager
import datetime
import json

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

class FindingPayload(BaseModel):
    severity: str
    title: str

class AgentSyncPayload(BaseModel):
    event_type: str
    timestamp: str
    finding: FindingPayload
    repo: str

@router.post("/agent-sync")
async def agent_sync(payload: AgentSyncPayload):
    """
    Receives real-time finding telemetry from the autonomous agent.py running on GitHub Actions.
    Broadcasts the finding to connected dashboard clients via WebSockets.
    """
    # Create a message to broadcast
    message = {
        "type": "live_finding",
        "data": {
            "title": payload.finding.title,
            "severity": payload.finding.severity,
            "repo": payload.repo,
            "timestamp": payload.timestamp
        }
    }
    
    # Broadcast to all connected clients on the 'dashboard' channel
    await twin_ws_manager.broadcast("dashboard", message)
    
    return {"status": "success", "message": "Telemetry received and broadcasted"}
