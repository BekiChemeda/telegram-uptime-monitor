from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.connection import get_db
from app.models import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/create", response_model=UserResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(User).filter(User.telegram_id == user.telegram_id))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create user dictionary and filter out None values to let DB defaults handle them
    user_data = {
        "telegram_id": user.telegram_id,
        "username": user.username,
    }
    if user.created_at:
        user_data["joined_at"] = user.created_at

    new_user = User(**user_data)
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user