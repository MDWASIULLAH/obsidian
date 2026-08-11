from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.live_scan import trigger_real_scan
from app.models.database import get_db
from app.models.schemas import ScanCreate, ScanResponse

router = APIRouter(tags=["scans"])


@router.post("/scans", response_model=ScanResponse)
async def trigger_scan_compat(
    data: ScanCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """Make the existing POST /scans endpoint use the real repository scanner."""
    return await trigger_real_scan(data, background_tasks, db)
