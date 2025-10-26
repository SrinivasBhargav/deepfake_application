from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .db import Base

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="PENDING", index=True)
    media_type: Mapped[str] = mapped_column(String, default="unknown")
    filename: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Result(Base):
    __tablename__ = "results"
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), primary_key=True)
    score: Mapped[float] = mapped_column(Float)
    message: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
