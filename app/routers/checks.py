from turtle import update
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.connection import get_db
from app.models import User, CheckLog
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