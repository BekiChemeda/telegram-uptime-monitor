import uuid
from fastapi import FastAPI
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.connection import get_db
from app.models import User, Monitor
from app.schemas.monitor import MonitorCreate, MonitorResponse, MonitorUpdate
from app.security import require_api_key

router = APIRouter(
    prefix="/monitors",
    tags=["monitors"],
    dependencies=[Depends(require_api_key)]
)
@router.post("/create", response_model=MonitorResponse)
async def create_monitor(monitor: MonitorCreate, db: AsyncSession = Depends(get_db)):
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
        is_active=monitor.is_active,
        # Pro Features
        check_ssl=monitor.check_ssl,
        ssl_expiry_days_threshold=monitor.ssl_expiry_days_threshold,
        keyword_include=monitor.keyword_include,
        keyword_exclude=monitor.keyword_exclude,
        max_response_time=monitor.max_response_time,
        consecutive_checks=monitor.consecutive_checks
    )
    db.add(new_monitor)
    await db.commit()
    await db.refresh(new_monitor)
    return new_monitor

@router.get("/user/{telegram_id}", response_model=list[MonitorResponse])
async def get_monitors(telegram_id: int, db: AsyncSession = Depends(get_db)):
    owner = await db.execute(select(User).filter(User.telegram_id == telegram_id))
    existing_user = owner.scalars().first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    monitors_query = await db.execute(select(Monitor).filter(Monitor.owner_id == existing_user.id))
    monitors = monitors_query.scalars().all()
    return monitors


@router.get("/monitor/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(monitor_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    monitor_query = await db.execute(select(Monitor).filter(Monitor.id == monitor_id))
    monitor = monitor_query.scalars().first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.delete("/{monitor_id}", response_model=dict)
async def delete_monitor(monitor_id: uuid.UUID, telegram_id: int, db: AsyncSession = Depends(get_db)):
    owner = await db.execute(select(User).filter(User.telegram_id == telegram_id))
    existing_user = owner.scalars().first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    monitor_query = await db.execute(select(Monitor).filter(Monitor.id == monitor_id))
    existing_monitor = monitor_query.scalars().first()
    
    if not existing_monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
        
    if existing_monitor.owner_id != existing_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this monitor")
    
    await db.delete(existing_monitor)
    await db.commit()
    return {"detail": "Monitor deleted successfully"}

@router.put("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(monitor_id: uuid.UUID, monitor_update: MonitorUpdate, db: AsyncSession = Depends(get_db)):
    # Verify User
    user_query = await db.execute(select(User).filter(User.telegram_id == monitor_update.telegram_id))
    user = user_query.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    monitor_query = await db.execute(select(Monitor).filter(Monitor.id == monitor_id))
    monitor = monitor_query.scalars().first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    if monitor.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this monitor")
    
    if monitor_update.url is not None:
        monitor.url = str(monitor_update.url)
    if monitor_update.name is not None:
        monitor.name = monitor_update.name
    if monitor_update.interval_seconds is not None:
        monitor.interval_seconds = monitor_update.interval_seconds
    if monitor_update.timeout_seconds is not None:
        monitor.timeout_seconds = monitor_update.timeout_seconds
    if monitor_update.expected_status is not None:
        monitor.expected_status = monitor_update.expected_status
    if monitor_update.is_active is not None:
        monitor.is_active = monitor_update.is_active
        
    # Pro Features
    if monitor_update.check_ssl is not None:
        monitor.check_ssl = monitor_update.check_ssl
    if monitor_update.ssl_expiry_days_threshold is not None:
        monitor.ssl_expiry_days_threshold = monitor_update.ssl_expiry_days_threshold
    if monitor_update.keyword_include is not None:
        monitor.keyword_include = monitor_update.keyword_include
    if monitor_update.keyword_exclude is not None:
        monitor.keyword_exclude = monitor_update.keyword_exclude
    if monitor_update.max_response_time is not None:
        monitor.max_response_time = monitor_update.max_response_time
    if monitor_update.consecutive_checks is not None:
        monitor.consecutive_checks = monitor_update.consecutive_checks

    await db.commit()
    await db.refresh(monitor)
    return monitor

@router.get("", response_model=list[MonitorResponse])
async def get_all_monitors(db: AsyncSession = Depends(get_db)):
    monitors_query = await db.execute(select(Monitor))
    monitors = monitors_query.scalars().all()
    return monitors