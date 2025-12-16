from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
import pandas as pd

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.recommendation_engine import recommendation_engine
from app.models import User, UserResourceInteraction, Resource
from app.schemas.resource import Resource as ResourceSchema

router = APIRouter()


@router.get("/recommendations/{user_id}", response_model=List[ResourceSchema])
async def get_user_recommendations(
    user_id: int,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized resource recommendations for a user"""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these recommendations"
        )

    try:
        # Get user data
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get user preferences
        from app.models.resource import UserPreference
        preferences = db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()

        user_data = {
            'learning_style': user.learning_style,
            'experience_level': user.experience_level,
            'preferred_difficulty': preferences.preferred_difficulty if preferences else None,
            'preferred_learning_style': preferences.preferred_learning_style if preferences else None,
            'preferred_media_types': preferences.preferred_media_types if preferences else None,
        }

        # Get user interaction history
        interactions = db.query(UserResourceInteraction).filter(
            UserResourceInteraction.user_id == user_id
        ).order_by(desc(UserResourceInteraction.created_at)).all()

        user_interactions = [
            {
                'resource_id': interaction.resource_id,
                'interaction_type': interaction.interaction_type,
                'rating': interaction.rating,
                'created_at': interaction.created_at
            }
            for interaction in interactions
        ]

        # Get all resources for recommendation
        resources = db.query(Resource).all()
        resources_df = pd.DataFrame([
            {
                'id': r.id,
                'title': r.title,
                'description': r.description or '',
                'url': r.url,
                'media_type': r.media_type,
                'difficulty': r.difficulty,
                'duration_minutes': r.duration_minutes,
                'rating': r.rating,
                'rating_count': r.rating_count,
                'tags': r.tags or [],
                'prerequisites': r.prerequisites or [],
                'learning_style': r.learning_style,
                'source': r.source
            }
            for r in resources
        ])

        # Get recommendations
        recommendations = recommendation_engine.get_recommendations(
            user_id=user_id,
            user_data=user_data,
            user_interactions=user_interactions,
            resources_df=resources_df,
            limit=limit
        )

        # Convert to ResourceSchema format
        result = []
        for rec in recommendations:
            resource = db.query(Resource).filter(Resource.id == rec['id']).first()
            if resource:
                result.append(resource)

        return result

    except Exception as e:
        # Fallback to simple popularity-based recommendations
        return await _get_fallback_recommendations(db, limit)


@router.get("/recommendations/popular", response_model=List[ResourceSchema])
async def get_popular_recommendations(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get popular resources as recommendations (no auth required)"""
    return await _get_fallback_recommendations(db, limit)


async def _get_fallback_recommendations(db: Session, limit: int) -> List[Resource]:
    """Fallback recommendations using popularity"""
    try:
        popular_resources = db.query(Resource).filter(
            Resource.rating_count > 0
        ).order_by(
            desc(Resource.rating),
            desc(Resource.rating_count)
        ).limit(limit).all()

        return popular_resources

    except Exception as e:
        # Ultimate fallback: just return some resources
        return db.query(Resource).limit(limit).all()


@router.post("/recommendations/train")
async def train_recommendation_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger recommendation model training (admin only)"""
    # TODO: Add admin check
    try:
        # Get training data
        interactions = db.query(UserResourceInteraction).all()
        resources = db.query(Resource).all()

        interactions_df = pd.DataFrame([
            {
                'user_id': i.user_id,
                'resource_id': i.resource_id,
                'interaction_type': i.interaction_type,
                'rating': i.rating,
                'created_at': i.created_at
            }
            for i in interactions
        ])

        resources_df = pd.DataFrame([
            {
                'id': r.id,
                'title': r.title,
                'description': r.description or '',
                'url': r.url,
                'media_type': r.media_type,
                'difficulty': r.difficulty,
                'duration_minutes': r.duration_minutes,
                'rating': r.rating,
                'rating_count': r.rating_count,
                'tags': r.tags or [],
                'prerequisites': r.prerequisites or [],
                'learning_style': r.learning_style,
                'source': r.source
            }
            for r in resources
        ])

        # Train models
        recommendation_engine.train_models(interactions_df, resources_df)

        return {"message": "Recommendation models trained successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(e)}"
        )


@router.get("/recommendations/similar/{resource_id}", response_model=List[ResourceSchema])
async def get_similar_resources(
    resource_id: int,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """Get resources similar to the given resource"""
    try:
        # Get the target resource
        target_resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if not target_resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )

        # Simple similarity based on tags, difficulty, and media type
        similar_resources = db.query(Resource).filter(
            Resource.id != resource_id
        )

        # Tag overlap scoring
        if target_resource.tags:
            similar_resources = similar_resources.filter(
                Resource.tags.overlap(target_resource.tags)
            )

        # Same difficulty and media type boost
        if target_resource.difficulty:
            similar_resources = similar_resources.filter(
                Resource.difficulty == target_resource.difficulty
            )

        if target_resource.media_type:
            similar_resources = similar_resources.filter(
                Resource.media_type == target_resource.media_type
            )

        # Order by rating and return top results
        similar_resources = similar_resources.order_by(
            desc(Resource.rating),
            desc(Resource.rating_count)
        ).limit(limit).all()

        return similar_resources

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find similar resources"
        )