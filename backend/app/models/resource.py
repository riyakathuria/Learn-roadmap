from sqlalchemy import Column, Integer, String, TIMESTAMP, text, VARCHAR, TEXT, ForeignKey, DECIMAL, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(VARCHAR(255), nullable=False)
    description = Column(TEXT)
    url = Column(VARCHAR(500), nullable=False)
    media_type = Column(VARCHAR(50), nullable=False)  # video, article, course, book, podcast, etc.
    difficulty = Column(VARCHAR(50))  # beginner, intermediate, advanced
    duration_minutes = Column(Integer)
    rating = Column(DECIMAL(3, 2), default=0)
    rating_count = Column(Integer, default=0)
    tags = Column(JSON)  # JSON array of tags
    prerequisites = Column(JSON)  # JSON array of prerequisite descriptions
    learning_style = Column(VARCHAR(50))  # visual, auditory, kinesthetic, reading
    source = Column(VARCHAR(100))  # platform name
    scraped_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    interactions = relationship("UserResourceInteraction", back_populates="resource", cascade="all, delete-orphan")
    step_resources = relationship("StepResource", back_populates="resource", cascade="all, delete-orphan")


class StepResource(Base):
    __tablename__ = "step_resources"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("roadmap_steps.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    is_recommended = Column(Boolean, default=True)
    order_index = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    step = relationship("RoadmapStep", back_populates="step_resources")
    resource = relationship("Resource", back_populates="step_resources")


class UserResourceInteraction(Base):
    __tablename__ = "user_resource_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_type = Column(VARCHAR(50), nullable=False)  # view, like, rate, complete, save
    rating = Column(Integer)  # 1-5 stars
    review = Column(TEXT)
    time_spent_minutes = Column(Integer)
    completed = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="resource_interactions")
    resource = relationship("Resource", back_populates="interactions")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    preferred_media_types = Column(JSON)  # JSON array of preferred resource types
    preferred_difficulty = Column(VARCHAR(50))
    preferred_learning_style = Column(VARCHAR(50))
    max_duration_minutes = Column(Integer)
    avoid_tags = Column(JSON)  # JSON array of tags to avoid
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preferences")