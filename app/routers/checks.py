from turtle import update
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.connection import get_db
from app.models import Monitor, User, CheckLog
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(
    prefix="/checks",
    tags=["checks"]
)


## This endpoint saves the log of a check performed by the bot.
@router.post("/log", response_model=CheckLog)
async def log_check(check_log: CheckLog, db: AsyncSession = Depends(get_db)):
    try:
        db.add(check_log)
        await db.commit()
        await db.refresh(check_log)
        return check_log
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
## This endpoint retrieves all check logs from the database for admin only.
@router.get("/logs", response_model=list[CheckLog])
async def get_check_logs(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(CheckLog))
        check_logs = result.scalars().all()
        return check_logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
## This endpoint retrieves check logs for a specific user.
@router.get("/logs/users/{user_id}", response_model=list[CheckLog])
async def get_user_check_logs(user_id: int, db: AsyncSession = Depends(get_db)):
    UserQuery = select(User).where(User.id == user_id)
    result = await db.execute(UserQuery)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="User not found")
    try:
        result = await db.execute(select(CheckLog).where(CheckLog.user_id == user_id))
        check_logs = result.scalars().all()
        return check_logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

## This endpoint deletes all check logs for a specific monitored entity.
@router.delete("/logs/monitors/{monitor_id}", response_model=list[CheckLog])
async def get_monitor_check_logs(monitor_id: int, db: AsyncSession = Depends(get_db)):
    MonitorQuery = select(Monitor).where(Monitor.id == monitor_id)
    result = await db.execute(MonitorQuery)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Monitor not found")
    try:
        result = await db.execute(select(CheckLog).where(CheckLog.monitor_id == monitor_id))
        check_logs = result.scalars().all()
        for log in check_logs:
            await db.delete(log)
        await db.commit()
        return check_logs
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))