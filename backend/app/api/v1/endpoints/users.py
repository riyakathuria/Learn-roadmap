from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User, UserPreference
from app.schemas.user import (
    User as UserSchema,
    UserUpdate,
    UserPreferences,
    UserPreferencesUpdate
)

router = APIRouter()


@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get user profile by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile (admin or self only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Only allow users to update their own profile (or implement admin check later)
    if user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Update failed"
        )


@router.get("/{user_id}/preferences", response_model=UserPreferences)
async def get_user_preferences(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these preferences"
        )

    preferences = db.query(UserPreference).filter(
        UserPreference.user_id == user_id
    ).first()

    if not preferences:
        # Return default preferences if none exist
        return UserPreferences()

    return UserPreferences(
        preferred_media_types=preferences.preferred_media_types,
        preferred_difficulty=preferences.preferred_difficulty,
        preferred_learning_style=preferences.preferred_learning_style,
        max_duration_minutes=preferences.max_duration_minutes,
        avoid_tags=preferences.avoid_tags
    )


@router.put("/{user_id}/preferences", response_model=UserPreferences)
async def update_user_preferences(
    user_id: int,
    preferences_update: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update these preferences"
        )

    preferences = db.query(UserPreference).filter(
        UserPreference.user_id == user_id
    ).first()

    update_data = preferences_update.dict(exclude_unset=True)

    if preferences:
        # Update existing preferences
        for field, value in update_data.items():
            setattr(preferences, field, value)
    else:
        # Create new preferences
        preferences = UserPreference(
            user_id=user_id,
            **update_data
        )
        db.add(preferences)

    try:
        db.commit()
        db.refresh(preferences)

        return UserPreferences(
            preferred_media_types=preferences.preferred_media_types,
            preferred_difficulty=preferences.preferred_difficulty,
            preferred_learning_style=preferences.preferred_learning_style,
            max_duration_minutes=preferences.max_duration_minutes,
            avoid_tags=preferences.avoid_tags
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preferences update failed"
        )


@router.get("/{user_id}/history")
async def get_user_history(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user learning history (placeholder for now)"""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this history"
        )

    # This will be implemented when we add resource interactions
    # For now, return empty history
    return {
        "user_id": user_id,
        "total_resources_completed": 0,
        "total_time_spent": 0,
        "recent_activity": [],
        "learning_streak": 0
    }