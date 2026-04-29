"""
Database Configuration Module

This module provides database engine, session maker, and base models
to avoid circular imports between server.py and other modules.
"""

import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Get ROOT_DIR from environment or calculate it
ROOT_DIR = Path(__file__).parent

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT_DIR}/keda_dashboard.db")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create async session maker
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Base class for ORM models
class Base(DeclarativeBase):
    pass
