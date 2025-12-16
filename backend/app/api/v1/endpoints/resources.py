from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc, asc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.cache import cache_get, cache_set, get_cache_key
from app.models.user import User
from app.models.resource import Resource, UserResourceInteraction
from app.schemas.resource import (
    Resource as ResourceSchema,
    ResourceCreate,
    ResourceUpdate,
    ResourceSearchQuery,
    ResourceRating,
    ResourceInteraction,
    ResourceWithInteractions
)

router = APIRouter()


def _get_user_interactions_dict(user_id: int, resource_ids: List[int], db: Session) -> dict:
    """Helper function to get user interactions for multiple resources"""
    if not user_id or not resource_ids:
        return {}

    interactions = db.query(UserResourceInteraction).filter(
        UserResourceInteraction.user_id == user_id,
        UserResourceInteraction.resource_id.in_(resource_ids)
    ).all()

    result = {}
    for interaction in interactions:
        if interaction.resource_id not in result:
            result[interaction.resource_id] = {
                'rating': None,
                'completed': False,
                'saved': False,
                'time_spent': 0
            }

        if interaction.interaction_type == 'rate':
            result[interaction.resource_id]['rating'] = interaction.rating
        elif interaction.interaction_type == 'complete':
            result[interaction.resource_id]['completed'] = True
        elif interaction.interaction_type == 'save':
            result[interaction.resource_id]['saved'] = True
        elif interaction.interaction_type == 'view':
            result[interaction.resource_id]['time_spent'] += interaction.time_spent_minutes or 0

    return result


@router.get("/search", response_model=List[ResourceWithInteractions])
async def search_resources(
    q: Optional[str] = Query(None, description="Search query"),
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    learning_style: Optional[str] = Query(None, description="Filter by learning style"),
    min_duration: Optional[int] = Query(None, description="Minimum duration in minutes"),
    max_duration: Optional[int] = Query(None, description="Maximum duration in minutes"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    source: Optional[str] = Query(None, description="Filter by source"),
    sort_by: Optional[str] = Query("rating", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Search and filter resources with pagination"""

    # Build query
    query = db.query(Resource)

    # Apply search filters
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Resource.title.ilike(search_term),
                Resource.description.ilike(search_term),
                Resource.tags.any(search_term)
            )
        )

    if media_type:
        query = query.filter(Resource.media_type == media_type)

    if difficulty:
        query = query.filter(Resource.difficulty == difficulty)

    if learning_style:
        query = query.filter(Resource.learning_style == learning_style)

    if min_duration is not None:
        query = query.filter(Resource.duration_minutes >= min_duration)

    if max_duration is not None:
        query = query.filter(Resource.duration_minutes <= max_duration)

    if tags:
        # Filter resources that have any of the specified tags
        query = query.filter(Resource.tags.overlap(tags))

    if source:
        query = query.filter(Resource.source.ilike(f"%{source}%"))

    # Apply sorting
    sort_column = getattr(Resource, sort_by, Resource.rating)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Apply pagination
    offset = (page - 1) * per_page
    resources = query.offset(offset).limit(per_page).all()

    # Get user interactions if user is authenticated
    user_interactions = {}
    if current_user:
        resource_ids = [r.id for r in resources]
        user_interactions = _get_user_interactions_dict(current_user.id, resource_ids, db)

    # Format response with user interactions
    result = []
    for resource in resources:
        interactions = user_interactions.get(resource.id, {})
        resource_dict = {
            **resource.__dict__,
            'user_rating': interactions.get('rating'),
            'user_completed': interactions.get('completed'),
            'user_saved': interactions.get('saved'),
            'user_time_spent': interactions.get('time_spent')
        }
        result.append(ResourceWithInteractions(**resource_dict))

    return result


@router.get("/{resource_id}", response_model=ResourceWithInteractions)
async def get_resource(
    resource_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get detailed resource information"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Get user interactions if authenticated
    user_interactions = {}
    if current_user:
        user_interactions = _get_user_interactions_dict(current_user.id, [resource_id], db)

    interactions = user_interactions.get(resource_id, {})
    resource_dict = {
        **resource.__dict__,
        'user_rating': interactions.get('rating'),
        'user_completed': interactions.get('completed'),
        'user_saved': interactions.get('saved'),
        'user_time_spent': interactions.get('time_spent')
    }

    return ResourceWithInteractions(**resource_dict)


@router.post("/{resource_id}/rate", response_model=dict)
async def rate_resource(
    resource_id: int,
    rating_data: ResourceRating,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rate a resource and optionally add a review"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    try:
        # Check if user already rated this resource
        existing_rating = db.query(UserResourceInteraction).filter(
            UserResourceInteraction.user_id == current_user.id,
            UserResourceInteraction.resource_id == resource_id,
            UserResourceInteraction.interaction_type == 'rate'
        ).first()

        if existing_rating:
            # Update existing rating
            existing_rating.rating = rating_data.rating
            existing_rating.review = rating_data.review
            existing_rating.updated_at = datetime.utcnow()
        else:
            # Create new rating interaction
            interaction = UserResourceInteraction(
                user_id=current_user.id,
                resource_id=resource_id,
                interaction_type='rate',
                rating=rating_data.rating,
                review=rating_data.review
            )
            db.add(interaction)

        # Update resource aggregate rating
        ratings = db.query(UserResourceInteraction).filter(
            UserResourceInteraction.resource_id == resource_id,
            UserResourceInteraction.interaction_type == 'rate',
            UserResourceInteraction.rating.isnot(None)
        ).all()

        if ratings:
            avg_rating = sum(r.rating for r in ratings) / len(ratings)
            resource.rating = round(avg_rating, 2)
            resource.rating_count = len(ratings)

        db.commit()

        return {"message": "Rating submitted successfully", "rating": rating_data.rating}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit rating"
        )


@router.post("/{resource_id}/complete", response_model=dict)
async def mark_resource_complete(
    resource_id: int,
    time_spent_minutes: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a resource as completed"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    try:
        # Check if user already completed this resource
        existing_completion = db.query(UserResourceInteraction).filter(
            UserResourceInteraction.user_id == current_user.id,
            UserResourceInteraction.resource_id == resource_id,
            UserResourceInteraction.interaction_type == 'complete'
        ).first()

        if existing_completion:
            # Update time spent if provided
            if time_spent_minutes is not None:
                existing_completion.time_spent_minutes = time_spent_minutes
                existing_completion.updated_at = datetime.utcnow()
        else:
            # Create new completion interaction
            interaction = UserResourceInteraction(
                user_id=current_user.id,
                resource_id=resource_id,
                interaction_type='complete',
                time_spent_minutes=time_spent_minutes,
                completed=True
            )
            db.add(interaction)

        db.commit()

        return {"message": "Resource marked as completed"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark resource as completed"
        )


@router.post("/{resource_id}/interaction", response_model=dict)
async def record_interaction(
    resource_id: int,
    interaction_data: ResourceInteraction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a user interaction with a resource"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    try:
        # Create interaction record
        interaction = UserResourceInteraction(
            user_id=current_user.id,
            resource_id=resource_id,
            interaction_type=interaction_data.interaction_type,
            rating=interaction_data.rating,
            review=interaction_data.review,
            time_spent_minutes=interaction_data.time_spent_minutes,
            completed=interaction_data.interaction_type == 'complete'
        )
        db.add(interaction)
        db.commit()

        return {"message": f"Interaction '{interaction_data.interaction_type}' recorded successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record interaction"
        )


@router.get("/recommendations/{user_id}", response_model=List[ResourceSchema])
async def get_recommendations(
    user_id: int,
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized resource recommendations for a user"""
    # For now, return highly rated resources
    # This will be replaced with proper recommendation engine later

    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these recommendations"
        )

    # Simple recommendation: get highly rated resources user hasn't interacted with
    interacted_resource_ids = db.query(UserResourceInteraction.resource_id).filter(
        UserResourceInteraction.user_id == user_id
    ).distinct().subquery()

    recommendations = db.query(Resource).filter(
        ~Resource.id.in_(interacted_resource_ids)
    ).order_by(
        desc(Resource.rating),
        desc(Resource.rating_count)
    ).limit(limit).all()

    return recommendations


@router.post("/scrape", response_model=dict)
async def trigger_resource_scraping(
    query: Optional[str] = Query(None, description="Search query for Coursera courses"),
    limit: int = Query(20, ge=1, le=100, description="Number of courses to scrape"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger resource scraping from Coursera API (admin only)"""
    # TODO: Implement admin check
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")

    try:
        from app.core.course_api import fetch_coursera_courses
        import asyncio

        # Run the async function in a thread pool since we're in a sync endpoint
        # In production, this should be a background task
        courses = await fetch_coursera_courses(query=query or "", limit=limit)

        # Store courses in database
        added_count = 0
        for course_data in courses:
            try:
                # Check if course already exists
                existing = db.query(Resource).filter(
                    Resource.external_id == course_data.get("external_id")
                ).first()

                if not existing:
                    # Create new resource
                    resource = Resource(**course_data)
                    db.add(resource)
                    added_count += 1
                else:
                    # Update existing resource
                    for key, value in course_data.items():
                        if hasattr(existing, key) and key not in ['id', 'created_at']:
                            setattr(existing, key, value)
                    existing.updated_at = course_data.get("updated_at")

            except Exception as e:
                # Log error but continue with other courses
                print(f"Error saving course {course_data.get('title')}: {str(e)}")
                continue

        db.commit()

        return {
            "message": f"Successfully scraped and added {added_count} courses from Coursera",
            "status": "completed",
            "courses_scraped": len(courses),
            "courses_added": added_count
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape courses: {str(e)}"
        )


@router.post("/sync-coursera", response_model=dict)
async def sync_coursera_courses(
    query: Optional[str] = Query(None, description="Search query for Coursera courses"),
    limit: int = Query(50, ge=1, le=200, description="Number of courses to sync"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync latest courses from Coursera API"""
    # TODO: Implement admin check

    try:
        from app.core.course_api import fetch_coursera_courses
        import asyncio

        # Fetch courses from Coursera
        courses = await fetch_coursera_courses(query=query or "", limit=limit)

        # Update or insert courses
        updated_count = 0
        added_count = 0

        for course_data in courses:
            try:
                external_id = course_data.get("external_id")
                existing = db.query(Resource).filter(
                    Resource.external_id == external_id
                ).first()

                if existing:
                    # Update existing course
                    for key, value in course_data.items():
                        if hasattr(existing, key) and key not in ['id', 'created_at']:
                            setattr(existing, key, value)
                    existing.updated_at = course_data.get("updated_at")
                    updated_count += 1
                else:
                    # Add new course
                    resource = Resource(**course_data)
                    db.add(resource)
                    added_count += 1

            except Exception as e:
                print(f"Error syncing course {course_data.get('title')}: {str(e)}")
                continue

        db.commit()

        return {
            "message": f"Synced {added_count + updated_count} courses from Coursera",
            "status": "completed",
            "courses_added": added_count,
            "courses_updated": updated_count
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync courses: {str(e)}"
        )