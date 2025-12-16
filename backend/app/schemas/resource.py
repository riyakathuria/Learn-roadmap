from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, List
from datetime import datetime


class ResourceBase(BaseModel):
    title: str
    description: Optional[str] = None
    url: HttpUrl
    media_type: str
    difficulty: Optional[str] = None
    duration_minutes: Optional[int] = None
    tags: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    learning_style: Optional[str] = None
    source: Optional[str] = None

    @validator('media_type')
    def validate_media_type(cls, v):
        valid_types = ['video', 'article', 'course', 'book', 'podcast', 'tutorial', 'documentation']
        if v and v not in valid_types:
            raise ValueError(f'Invalid media type. Must be one of: {", ".join(valid_types)}')
        return v

    @validator('difficulty')
    def validate_difficulty(cls, v):
        if v and v not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError('Invalid difficulty level')
        return v

    @validator('learning_style')
    def validate_learning_style(cls, v):
        if v and v not in ['visual', 'auditory', 'kinesthetic', 'reading']:
            raise ValueError('Invalid learning style')
        return v


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[HttpUrl] = None
    media_type: Optional[str] = None
    difficulty: Optional[str] = None
    duration_minutes: Optional[int] = None
    tags: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    learning_style: Optional[str] = None
    source: Optional[str] = None


class Resource(ResourceBase):
    id: int
    rating: float
    rating_count: int
    scraped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResourceSearchFilters(BaseModel):
    media_type: Optional[str] = None
    difficulty: Optional[str] = None
    learning_style: Optional[str] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None


class ResourceSearchQuery(BaseModel):
    q: Optional[str] = None
    filters: Optional[ResourceSearchFilters] = None
    sort_by: Optional[str] = "rating"
    sort_order: Optional[str] = "desc"
    page: Optional[int] = 1
    per_page: Optional[int] = 20

    @validator('sort_by')
    def validate_sort_by(cls, v):
        valid_fields = ['title', 'rating', 'rating_count', 'created_at', 'duration_minutes']
        if v and v not in valid_fields:
            raise ValueError(f'Invalid sort field. Must be one of: {", ".join(valid_fields)}')
        return v

    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v and v.lower() not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v.lower() if v else v


class ResourceRating(BaseModel):
    rating: int
    review: Optional[str] = None

    @validator('rating')
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class ResourceInteraction(BaseModel):
    resource_id: int
    interaction_type: str  # 'view', 'like', 'rate', 'complete', 'save'
    rating: Optional[int] = None
    review: Optional[str] = None
    time_spent_minutes: Optional[int] = None

    @validator('interaction_type')
    def validate_interaction_type(cls, v):
        valid_types = ['view', 'like', 'rate', 'complete', 'save']
        if v not in valid_types:
            raise ValueError(f'Invalid interaction type. Must be one of: {", ".join(valid_types)}')
        return v

    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class ResourceWithInteractions(Resource):
    user_rating: Optional[int] = None
    user_completed: Optional[bool] = None
    user_saved: Optional[bool] = None
    user_time_spent: Optional[int] = None