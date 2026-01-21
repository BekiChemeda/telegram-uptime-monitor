from fastapi import FastAPI
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.connection import get_db
from app.models import User, Monitor
from app.schemas import user
from app.schemas.monitor import MonitorCreate, MonitorResponse

router = APIRouter(
    prefix="/monitors",
    tags=["monitors"]
)
@router.post("/create", response_model=MonitorResponse)
async def create_model(monitor: MonitorCreate, db: AsyncSession = Depends(get_db)):
    owner = await db.execute(select(User).filter(User.telegram_id == monitor.telegram_id))
    existing_user = owner.scalars().first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    monitor_query = await db.execute(select(Monitor).filter(Monitor.url == str(monitor.url), Monitor.owner_id == existing_user.id))
    existing_monitor = monitor_query.scalars().first()
    if existing_monitor:
        raise HTTPException(status_code=400, detail="Monitor already exists for this user")
    
    new_monitor = Monitor(
        url=str(monitor.url),
        owner_id=existing_user.id,
        name=monitor.name,
        interval_seconds=monitor.interval_seconds,
        timeout_seconds=monitor.timeout_seconds,
        expected_status=monitor.expected_status,
        is_active=monitor.is_active
    )
    db.add(new_monitor)
    await db.commit()
    await db.refresh(new_monitor)
    return new_monitor

@router.get("/{telegram_id}", response_model=list[MonitorResponse])
async def get_monitors(telegram_id: int, db: AsyncSession = Depends(get_db)):
    owner = await db.execute(select(User).filter(User.telegram_id == telegram_id))
    existing_user = owner.scalars().first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    monitors_query = await db.execute(select(Monitor).filter(Monitor.owner_id == existing_user.id))
    monitors = monitors_query.scalars().all()
    return monitors
    