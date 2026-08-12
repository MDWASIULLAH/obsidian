from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.live_scan import trigger_real_scan
from app.models.database import get_db
from app.models.finding import Finding
from app.models.patch import Patch
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus
from app.models.schemas import ScanCreate, ScanResponse, ScanSummary

router = APIRouter(tags=["scans", "dashboard"])


@router.post("/scans", response_model=ScanResponse)
async def trigger_scan_compat(
    data: ScanCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    return await trigger_real_scan(data, background_tasks, db)


@router.get("/dashboard")
async def live_dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    """Fast live dashboard source used before the legacy dashboard router."""
    repo_count = await db.execute(select(func.count(Repository.id)))
    total_repos = int(repo_count.scalar() or 0)

    active_values = [
        ScanStatus.QUEUED.value,
        ScanStatus.INDEXING.value,
        ScanStatus.SCANNING.value,
        ScanStatus.PATCHING.value,
        ScanStatus.TESTING.value,
        ScanStatus.REVIEWING.value,
    ]
    active_query = await db.execute(select(Scan).where(Scan.status.in_(active_values)).order_by(desc(Scan.created_at)))
    active_scans = list(active_query.scalars().all())
    latest_active = active_scans[0] if active_scans else None

    finding_counts = await db.execute(select(Finding.severity, func.count(Finding.id)).group_by(Finding.severity))
    distribution = {str(k): int(v) for k, v in finding_counts.all()}
    total_findings = sum(distribution.values())

    recent_result = await db.execute(select(Scan).order_by(desc(Scan.created_at)).limit(10))
    recent = [ScanSummary.model_validate(scan).model_dump() for scan in recent_result.scalars().all()]

    completed_scores = await db.execute(select(func.avg(Scan.security_score)).where(Scan.status == ScanStatus.COMPLETED.value))
    avg_score = completed_scores.scalar()

    patch_count = await db.execute(select(func.count(Patch.id)))

    state = "idle"
    progress = 0
    if latest_active:
        state = getattr(latest_active.status, "value", str(latest_active.status))
        progress_map = {
            ScanStatus.QUEUED.value: 5,
            ScanStatus.INDEXING.value: 20,
            ScanStatus.SCANNING.value: 50,
            ScanStatus.PATCHING.value: 70,
            ScanStatus.TESTING.value: 85,
            ScanStatus.REVIEWING.value: 95,
        }
        progress = progress_map.get(state, 0)
    elif recent:
        latest = recent[0]
        latest_status = str(latest.get("status", ""))
        if latest_status == ScanStatus.COMPLETED.value:
            state = "completed"
            progress = 100
        elif latest_status == ScanStatus.FAILED.value:
            state = "failed"
            progress = 0

    return {
        "total_repositories": total_repos,
        "active_scans": len(active_scans),
        "total_findings": total_findings,
        "critical_findings": distribution.get("critical", 0),
        "average_security_score": round(float(avg_score), 1) if avg_score is not None else 0,
        "patches_generated": int(patch_count.scalar() or 0),
        "tests_generated": 0,
        "recent_scans": recent,
        "severity_distribution": distribution,
        "scan_progress": progress,
        "scan_state": state,
        "last_updated": recent[0].get("created_at") if recent else None,
    }
