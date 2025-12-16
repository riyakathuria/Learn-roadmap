from sqlalchemy import Column, Integer, String, TIMESTAMP, text, VARCHAR
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(VARCHAR(255), unique=True, nullable=False, index=True)
    username = Column(VARCHAR(100), unique=True, nullable=False, index=True)
    password_hash = Column(VARCHAR(255), nullable=False)
    full_name = Column(VARCHAR(255))
    avatar_url = Column(VARCHAR(500))
    learning_style = Column(VARCHAR(50))  # visual, auditory, kinesthetic, reading
    experience_level = Column(VARCHAR(50))  # beginner, intermediate, advanced
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    roadmaps = relationship("Roadmap", back_populates="user", cascade="all, delete-orphan")
    resource_interactions = relationship("UserResourceInteraction", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")