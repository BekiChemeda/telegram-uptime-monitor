from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    telegramId = Column(Integer, unique=True, nullable=False)
    username = Column(String, unique=True)
    joinedAt = Column(DateTime, nullable=False, default=datetime.now().isoformat())


class Website(Base):
    __tablename__ = "websites"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    ownerId = Column(Integer, unique=True, nullable=False)
    url = Column(String, unique=True, nullable=False)
    createdAt = Column(DateTime, nullable=False, default=datetime.now().isoformat())
    lastChecked = Column(DateTime, nullable=False, default=datetime.now().isoformat())
