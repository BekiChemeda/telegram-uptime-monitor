from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.connection import get_db
from app.models import Monitor, User, CheckLog
from app.schemas.checks import CheckLogCreate, CheckLogResponse

router = APIRouter(
    prefix="/checks",
    tags=["checks"]
)


## This endpoint saves the log of a check performed by the bot.
@router.post("/log", response_model=CheckLogResponse, status_code=status.HTTP_201_CREATED)
async def log_check(check_log_in: CheckLogCreate, db: AsyncSession = Depends(get_db)):
    # Verify monitor exists
    result = await db.execute(select(Monitor).where(Monitor.id == check_log_in.monitor_id))
    monitor = result.scalars().first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    new_log = CheckLog(**check_log_in.model_dump())
    db.add(new_log)
    try:
        await db.commit()
        await db.refresh(new_log)
        return new_log
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
## This endpoint retrieves all check logs from the database for admin only.
@router.get("/logs", response_model=List[CheckLogResponse])
async def get_check_logs(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(CheckLog))
        check_logs = result.scalars().all()
        return check_logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
## This endpoint retrieves check logs for a specific user.
@router.get("/logs/users/{user_id}", response_model=List[CheckLogResponse])
async def get_user_check_logs(user_id: UUID, db: AsyncSession = Depends(get_db)):
    # Verify user exists
    user_query = select(User).where(User.id == user_id)
    result = await db.execute(user_query)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # CheckLog doesn't have user_id, join with Monitor to filter by owner_id
        stmt = select(CheckLog).join(Monitor).where(Monitor.owner_id == user_id)
        result = await db.execute(stmt)
        check_logs = result.scalars().all()
        return check_logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

## This endpoint deletes all check logs for a specific monitored entity.
@router.delete("/logs/monitors/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor_check_logs(monitor_id: UUID, db: AsyncSession = Depends(get_db)):
    monitor_query = select(Monitor).where(Monitor.id == monitor_id)
    result = await db.execute(monitor_query)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    try:
        result = await db.execute(select(CheckLog).where(CheckLog.monitor_id == monitor_id))
        check_logs = result.scalars().all()
        for log in check_logs:
            await db.delete(log)
        await db.commit()
        return None
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
