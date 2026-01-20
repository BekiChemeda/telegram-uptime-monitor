from turtle import update
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.connection import get_db
from app.models import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"]
)


## This endpoint checks if a user exists by telegram_id
@router.get("/me/{telegram_id}")
async def get_user(telegram_id: int, db: AsyncSession = Depends(get_db))-> bool:
    result = await db.execute(select(User).filter(User.telegram_id == telegram_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return True

# Endpoint to get all users for admin purposes
@router.get("/", response_model=list[UserResponse])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User))
        users = result.scalars().all()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving users: {str(e)}")

# This endpoint creates a new user
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
    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

# This endpoint updates user's username
@router.put("/update", response_model=UserResponse)
async def update_info(update: UserUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).filter(User.telegram_id == update.telegram_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")   
                 
        user.username = update.username
        
        await db.commit()
        await db.refresh(user)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user info: {str(e)}")


    