from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.orm import declarative_base
from datetime import datetime
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    telegramId = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, unique=True)
    joinedAt = Column(DateTime, nullable=False, default=datetime.now)


class Website(Base):
    __tablename__ = "websites"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    ownerId = Column(BigInteger, nullable=False)
    url = Column(String, unique=True, nullable=False)
    createdAt = Column(DateTime, nullable=False, default=datetime.now)
    lastChecked = Column(DateTime, nullable=False, default=datetime.now)
