from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.llm_service import llm_service
from app.core.recommendation_engine import recommendation_engine
from app.models.user import User
from app.models.roadmap import Roadmap, RoadmapStep
from app.models.resource import Resource, StepResource
from app.schemas.roadmap import (
    Roadmap as RoadmapSchema,
    RoadmapCreate,
    RoadmapUpdate,
    RoadmapGenerationRequest,
    RoadmapGenerationResponse,
    RoadmapStep as RoadmapStepSchema,
    RoadmapStepUpdate,
    RoadmapProgressUpdate,
    RoadmapProgressResponse
)

router = APIRouter()


@router.post("/generate", response_model=RoadmapGenerationResponse)
async def generate_roadmap(
    request: RoadmapGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new learning roadmap using LLM and recommendations"""
    try:
        # Get user preferences for personalization
        user_preferences = {}
        if hasattr(current_user, 'preferences') and current_user.preferences:
            user_preferences = {
                'learning_style': current_user.learning_style,
                'experience_level': current_user.experience_level,
                'preferred_difficulty': current_user.preferences.preferred_difficulty,
                'preferred_learning_style': current_user.preferences.preferred_learning_style,
                'preferred_media_types': current_user.preferences.preferred_media_types,
            }

        # Merge with request preferences
        if request.preferences:
            user_preferences.update(request.preferences)

        # Generate roadmap using LLM
        roadmap_data = llm_service.generate_roadmap(
            concept=request.concept,
            duration_weeks=request.duration_weeks,
            user_preferences=user_preferences
        )

        # Create roadmap in database
        roadmap = Roadmap(
            user_id=current_user.id,
            title=roadmap_data['title'],
            concept=request.concept,
            duration_weeks=request.duration_weeks,
            description=roadmap_data.get('description', ''),
            status='draft'
        )
        db.add(roadmap)
        db.commit()
        db.refresh(roadmap)

        # Create roadmap steps
        steps = []
        for i, step_data in enumerate(roadmap_data.get('steps', [])):
            step = RoadmapStep(
                roadmap_id=roadmap.id,
                title=step_data['title'],
                description=step_data.get('description', ''),
                order_index=step_data.get('order_index', i),
                estimated_hours=step_data.get('estimated_hours', 8),
                difficulty=step_data.get('difficulty', 'intermediate'),
                prerequisites=step_data.get('prerequisites', [])
            )
            db.add(step)
            steps.append(step)

        db.commit()

        # Refresh roadmap with steps
        roadmap = db.query(Roadmap).filter(Roadmap.id == roadmap.id).first()
        roadmap.steps = db.query(RoadmapStep).filter(RoadmapStep.roadmap_id == roadmap.id).order_by(RoadmapStep.order_index).all()

        # Get recommendations for the roadmap
        try:
            recommendations = await _generate_roadmap_recommendations(
                roadmap, roadmap.steps, current_user, db
            )
        except Exception as e:
            # If recommendation generation fails, return empty recommendations
            recommendations = []

        # Return full roadmap data using schema validation
        return RoadmapGenerationResponse(
            roadmap=RoadmapSchema.from_orm(roadmap),
            recommendations=recommendations,
            generation_metadata={
                'model_used': roadmap_data.get('model_version', 'unknown'),
                'generated_at': roadmap_data.get('generated_at'),
                'estimated_total_hours': roadmap_data.get('estimated_total_hours', 0)
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Roadmap generation failed: {str(e)}"
        )


async def _generate_roadmap_recommendations(
    roadmap: Roadmap,
    steps: List[RoadmapStep],
    user: User,
    db: Session
) -> List[dict]:
    """Generate resource recommendations for roadmap steps"""
    recommendations = []

    try:
        # Get all available resources
        resources = db.query(Resource).all()

        if not resources:
            return recommendations

        import pandas as pd
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

        # Get user data for personalization
        user_data = {
            'learning_style': user.learning_style,
            'experience_level': user.experience_level,
        }

        # Get user interaction history
        from app.models.resource import UserResourceInteraction
        interactions = db.query(UserResourceInteraction).filter(
            UserResourceInteraction.user_id == user.id
        ).all()

        user_interactions = [
            {
                'resource_id': i.resource_id,
                'interaction_type': i.interaction_type,
                'rating': i.rating,
                'created_at': i.created_at
            }
            for i in interactions
        ]

        # Generate AI-curated recommendations for each step
        for step in steps:
            try:
                # Use LLM to generate 3 specific resources for this step
                step_resources = llm_service.generate_step_resources(
                    step_title=step.title,
                    step_description=step.description or '',
                    concept=roadmap.concept,
                    difficulty=step.difficulty or 'intermediate'
                )

                # Add each generated resource to recommendations
                for resource in step_resources:
                    recommendations.append({
                        'step_id': step.id,
                        'step_title': step.title,
                        'id': int(resource['id']),
                        'title': resource['title'],
                        'description': resource['description'],
                        'url': resource['url'],
                        'media_type': resource['media_type'],
                        'difficulty': resource['difficulty'],
                        'duration_minutes': int(resource['duration_minutes']),
                        'rating': float(resource['rating']),
                        'rating_count': int(resource['rating_count']),
                        'tags': resource['tags'],
                        'source': resource['source'],
                        'recommendation_score': float(resource['recommendation_score']),
                        'recommendation_reason': resource['recommendation_reason']
                    })

            except Exception as e:
                logger.error(f"Failed to generate resources for step {step.title}: {e}")
                # Fallback: use database resources if LLM fails
                step_relevant_resources = resources_df.head(3)  # Just take first 3 as fallback
                for _, resource_data in step_relevant_resources.iterrows():
                    recommendations.append({
                        'step_id': step.id,
                        'step_title': step.title,
                        'id': int(resource_data['id']),
                        'title': resource_data['title'],
                        'description': resource_data.get('description', ''),
                        'url': resource_data['url'],
                        'media_type': resource_data['media_type'],
                        'difficulty': resource_data.get('difficulty', 'intermediate'),
                        'duration_minutes': int(resource_data.get('duration_minutes', 60)),
                        'rating': float(resource_data.get('rating', 4.0)),
                        'rating_count': int(resource_data.get('rating_count', 0)),
                        'tags': resource_data.get('tags', []),
                        'source': resource_data.get('source', ''),
                        'recommendation_score': 0.7,
                        'recommendation_reason': f'Fallback resource for {step.title}'
                    })

        return recommendations

    except Exception as e:
        # Return empty recommendations if generation fails
        return []


@router.get("/", response_model=List[RoadmapSchema])
async def get_user_roadmaps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all roadmaps for the current user"""
    roadmaps = db.query(Roadmap).filter(
        Roadmap.user_id == current_user.id
    ).order_by(desc(Roadmap.created_at)).all()

    return roadmaps


@router.get("/{roadmap_id}", response_model=RoadmapSchema)
async def get_roadmap(
    roadmap_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific roadmap by ID"""
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()

    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found"
        )

    return roadmap


@router.put("/{roadmap_id}", response_model=RoadmapSchema)
async def update_roadmap(
    roadmap_id: int,
    roadmap_update: RoadmapUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a roadmap"""
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()

    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found"
        )

    update_data = roadmap_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(roadmap, field, value)

    try:
        db.commit()
        db.refresh(roadmap)
        return roadmap
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Roadmap update failed"
        )


@router.delete("/{roadmap_id}")
async def delete_roadmap(
    roadmap_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a roadmap"""
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()

    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found"
        )

    try:
        db.delete(roadmap)
        db.commit()
        return {"message": "Roadmap deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Roadmap deletion failed"
        )


@router.put("/{roadmap_id}/progress", response_model=RoadmapProgressResponse)
async def update_roadmap_progress(
    roadmap_id: int,
    progress_update: RoadmapProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update progress on a roadmap step"""
    # Find the roadmap
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()

    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found"
        )

    # Find the step
    step = db.query(RoadmapStep).filter(
        RoadmapStep.id == progress_update.step_id,
        RoadmapStep.roadmap_id == roadmap_id
    ).first()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )

    try:
        # Update step status
        if progress_update.completed:
            step.status = 'completed'
            step.completed_at = datetime.utcnow()
        else:
            step.status = 'in_progress'

        db.commit()

        # Calculate progress
        total_steps = len(roadmap.steps)
        completed_steps = len([s for s in roadmap.steps if s.status == 'completed'])

        progress_percentage = (completed_steps / total_steps) * 100 if total_steps > 0 else 0

        # Get next recommended steps
        next_steps = []
        for s in roadmap.steps:
            if s.status == 'pending':
                next_steps.append({
                    'id': s.id,
                    'title': s.title,
                    'estimated_hours': s.estimated_hours
                })
                if len(next_steps) >= 3:  # Limit to 3 recommendations
                    break

        return RoadmapProgressResponse(
            roadmap_id=roadmap_id,
            completed_steps=completed_steps,
            total_steps=total_steps,
            progress_percentage=progress_percentage,
            next_recommended_steps=next_steps
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Progress update failed"
        )


@router.get("/{roadmap_id}/steps", response_model=List[RoadmapStepSchema])
async def get_roadmap_steps(
    roadmap_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all steps for a roadmap"""
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()

    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found"
        )

    steps = db.query(RoadmapStep).filter(
        RoadmapStep.roadmap_id == roadmap_id
    ).order_by(RoadmapStep.order_index).all()

    return steps


@router.put("/{roadmap_id}/steps/{step_id}", response_model=RoadmapStepSchema)
async def update_roadmap_step(
    roadmap_id: int,
    step_id: int,
    step_update: RoadmapStepUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific roadmap step"""
    # Verify roadmap ownership
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()

    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found"
        )

    # Get the step
    step = db.query(RoadmapStep).filter(
        RoadmapStep.id == step_id,
        RoadmapStep.roadmap_id == roadmap_id
    ).first()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )

    update_data = step_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(step, field, value)

    try:
        db.commit()
        db.refresh(step)
        return step
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Step update failed"
        )
