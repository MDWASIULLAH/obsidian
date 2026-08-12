"""Live dashboard aggregation and first-run scan bootstrap."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.finding import Finding
from app.models.patch import Patch
from app.models.repository import Repository
from app.models.scan import Scan, ScanStatus
from app.models.schemas import ScanCreate, ScanSummary

router = APIRouter(tags=["dashboard"])

_PROGRESS = {
    ScanStatus.QUEUED.value: 10,
    ScanStatus.INDEXING.value: 25,
    ScanStatus.SCANNING.value: 55,
    ScanStatus.PATCHING.value: 72,
    ScanStatus.TESTING.value: 84,
    ScanStatus.REVIEWING.value: 95,
    ScanStatus.COMPLETED.value: 100,
    ScanStatus.FAILED.value: 100,
    ScanStatus.CANCELLED.value: 100,
}


@router.get("/dashboard")
async def live_dashboard(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return live dashboard data and bootstrap the first real repository scan."""
    repo_count = await db.execute(select(func.count(Repository.id)))
    total_repos = int(repo_count.scalar() or 0)

    scan_count_result = await db.execute(select(func.count(Scan.id)))
    total_scans = int(scan_count_result.scalar() or 0)

    # First visit: automatically start one real scan for the newest tracked repo.
    # The guard is the database scan count, so polling this endpoint never creates duplicates.
    if total_scans == 0 and total_repos > 0:
        repo_result = await db.execute(
            select(Repository).where(Repository.is_active.is_(True)).order_by(Repository.updated_at.desc()).limit(1)
        )
        repo = repo_result.scalar_one_or_none()
        if repo:
            try:
                from app.api.live_scan import trigger_real_scan
                await trigger_real_scan(
                    ScanCreate(repository_id=repo.id, commit_sha=repo.default_branch, branch=repo.default_branch),
                    background_tasks,
                    db,
                )
                total_scans = 1
            except Exception:
                # Dashboard must remain usable even if GitHub is temporarily unavailable.
                pass

    active_result = await db.execute(
        select(func.count(Scan.id)).where(
            Scan.status.in_([
                ScanStatus.QUEUED.value,
                ScanStatus.INDEXING.value,
                ScanStatus.SCANNING.value,
                ScanStatus.PATCHING.value,
                ScanStatus.TESTING.value,
                ScanStatus.REVIEWING.value,
            ])
        )
    )
    active_scans = int(active_result.scalar() or 0)

    finding_counts = await db.execute(
        select(Finding.severity, func.count(Finding.id)).group_by(Finding.severity)
    )
    severity_dist = {str(k): int(v) for k, v in finding_counts.all()}
    for key in ("critical", "high", "medium", "low", "info"):
        severity_dist.setdefault(key, 0)
    total_findings = sum(severity_dist.values())

    recent_result = await db.execute(select(Scan).order_by(Scan.created_at.desc()).limit(10))
    recent_scans = [ScanSummary.model_validate(s).model_dump() for s in recent_result.scalars().all()]

    completed_scores = await db.execute(
        select(func.avg(Scan.security_score)).where(Scan.status == ScanStatus.COMPLETED.value)
    )
    avg_score_raw = completed_scores.scalar()
    avg_score = round(float(avg_score_raw), 1) if avg_score_raw is not None else 0.0

    patch_result = await db.execute(select(func.count(Patch.id)))
    total_patches = int(patch_result.scalar() or 0)
    tests_result = await db.execute(select(func.coalesce(func.sum(Scan.tests_generated), 0)))
    total_tests = int(tests_result.scalar() or 0)

    latest = recent_scans[0] if recent_scans else None
    latest_status = str((latest or {}).get("status", "idle"))
    if hasattr(latest_status, "value"):
        latest_status = latest_status.value
    progress = _PROGRESS.get(latest_status, 0)
    if latest_status == ScanStatus.COMPLETED.value:
        progress = int(round(avg_score))

    return {
        "total_repositories": total_repos,
        "active_scans": active_scans,
        "total_findings": total_findings,
        "critical_findings": severity_dist["critical"],
        "average_security_score": avg_score,
        "patches_generated": total_patches,
        "tests_generated": total_tests,
        "recent_scans": recent_scans,
        "severity_distribution": severity_dist,
        "scan_progress": progress,
        "scan_state": latest_status,
        "last_updated": latest.get("created_at") if latest else None,
    }
