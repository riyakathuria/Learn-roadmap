from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class RoadmapStepBase(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int
    estimated_hours: Optional[int] = None
    difficulty: Optional[str] = None
    prerequisites: Optional[List[str]] = None
    status: Optional[str] = "pending"

    class Config:
        from_attributes = True

    @validator('difficulty')
    def validate_difficulty(cls, v):
        if v and v not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError('Invalid difficulty level')
        return v

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['pending', 'in_progress', 'completed']
        if v and v not in valid_statuses:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
        return v


class RoadmapStepCreate(RoadmapStepBase):
    pass


class RoadmapStep(RoadmapStepBase):
    id: Optional[int] = None
    roadmap_id: Optional[int] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoadmapStepUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    estimated_hours: Optional[int] = None
    difficulty: Optional[str] = None
    prerequisites: Optional[List[str]] = None
    status: Optional[str] = None
    completed_at: Optional[datetime] = None


class StepResourceAssignment(BaseModel):
    resource_id: int
    is_recommended: Optional[bool] = True
    order_index: Optional[int] = None


class RoadmapBase(BaseModel):
    title: str
    concept: str
    duration_weeks: int
    description: Optional[str] = None
    status: Optional[str] = "draft"

    @validator('duration_weeks')
    def validate_duration(cls, v):
        if v < 1 or v > 52:
            raise ValueError('Duration must be between 1 and 52 weeks')
        return v

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['draft', 'active', 'completed', 'archived']
        if v and v not in valid_statuses:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
        return v


class RoadmapCreate(RoadmapBase):
    steps: Optional[List[RoadmapStepCreate]] = None


class RoadmapUpdate(BaseModel):
    title: Optional[str] = None
    concept: Optional[str] = None
    duration_weeks: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None


class Roadmap(RoadmapBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    steps: List[RoadmapStep] = []

    class Config:
        from_attributes = True


class RoadmapGenerationRequest(BaseModel):
    concept: str
    duration_weeks: int
    preferences: Optional[Dict[str, Any]] = None

    @validator('concept')
    def validate_concept(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Concept must be at least 3 characters long')
        return v.strip()

    @validator('duration_weeks')
    def validate_duration(cls, v):
        if v < 1 or v > 52:
            raise ValueError('Duration must be between 1 and 52 weeks')
        return v


class RoadmapGenerationResponse(BaseModel):
    roadmap: Roadmap
    recommendations: List[Dict[str, Any]] = []
    generation_metadata: Optional[Dict[str, Any]] = None


class RoadmapProgressUpdate(BaseModel):
    step_id: int
    completed: bool
    rating: Optional[int] = None
    notes: Optional[str] = None

    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class RoadmapProgressResponse(BaseModel):
    roadmap_id: int
    completed_steps: int
    total_steps: int
    progress_percentage: float
    estimated_completion_date: Optional[datetime] = None
    next_recommended_steps: List[Dict[str, Any]] = []


class RoadmapAnalytics(BaseModel):
    total_roadmaps: int
    active_roadmaps: int
    completed_roadmaps: int
    average_completion_rate: float
    most_popular_concepts: List[Dict[str, str]] = []
    average_roadmap_duration: float


class RoadmapTemplate(BaseModel):
    name: str
    concept: str
    description: str
    difficulty: str
    estimated_duration_weeks: int
    tags: List[str] = []
    prerequisites: List[str] = []
    learning_objectives: List[str] = []

    @validator('difficulty')
    def validate_difficulty(cls, v):
        if v not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError('Invalid difficulty level')
        return v

    @validator('estimated_duration_weeks')
    def validate_duration(cls, v):
        if v < 1 or v > 52:
            raise ValueError('Duration must be between 1 and 52 weeks')
        return v