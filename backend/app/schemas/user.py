from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    learning_style: Optional[str] = None
    experience_level: Optional[str] = None

    @validator('learning_style')
    def validate_learning_style(cls, v):
        if v and v not in ['visual', 'auditory', 'kinesthetic', 'reading']:
            raise ValueError('Invalid learning style')
        return v

    @validator('experience_level')
    def validate_experience_level(cls, v):
        if v and v not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError('Invalid experience level')
        return v


class UserCreate(UserBase):
    password: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    learning_style: Optional[str] = None
    experience_level: Optional[str] = None
    avatar_url: Optional[str] = None


class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserPreferences(BaseModel):
    preferred_media_types: Optional[List[str]] = None
    preferred_difficulty: Optional[str] = None
    preferred_learning_style: Optional[str] = None
    max_duration_minutes: Optional[int] = None
    avoid_tags: Optional[List[str]] = None


class UserPreferencesUpdate(BaseModel):
    preferred_media_types: Optional[List[str]] = None
    preferred_difficulty: Optional[str] = None
    preferred_learning_style: Optional[str] = None
    max_duration_minutes: Optional[int] = None
    avoid_tags: Optional[List[str]] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str