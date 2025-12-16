from sqlalchemy import Column, Integer, String, TIMESTAMP, text, VARCHAR, TEXT, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(VARCHAR(255), nullable=False)
    concept = Column(VARCHAR(255), nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    description = Column(TEXT)
    status = Column(VARCHAR(50), server_default="draft")  # draft, active, completed, archived
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="roadmaps")
    steps = relationship("RoadmapStep", back_populates="roadmap", cascade="all, delete-orphan")


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(VARCHAR(255), nullable=False)
    description = Column(TEXT)
    order_index = Column(Integer, nullable=False)
    estimated_hours = Column(Integer)
    difficulty = Column(VARCHAR(50))  # beginner, intermediate, advanced
    prerequisites = Column(JSON)  # JSON array of prerequisite descriptions
    status = Column(VARCHAR(50), server_default="pending")  # pending, in_progress, completed
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap = relationship("Roadmap", back_populates="steps")
    step_resources = relationship("StepResource", back_populates="step", cascade="all, delete-orphan")