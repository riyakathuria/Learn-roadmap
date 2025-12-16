from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd

from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.vector_store import vector_store
from app.core.cache import cache_get, cache_set, get_cache_key
from app.models.user import User
from app.models.resource import Resource
from app.schemas.resource import ResourceSearchQuery, Resource as ResourceSchema

router = APIRouter()


@router.get("/semantic", response_model=List[ResourceSchema])
async def semantic_search(
    q: str = Query(..., description="Search query for semantic similarity"),
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    learning_style: Optional[str] = Query(None, description="Filter by learning style"),
    min_duration: Optional[int] = Query(None, description="Minimum duration in minutes"),
    max_duration: Optional[int] = Query(None, description="Maximum duration in minutes"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Semantic search using vector similarity"""
    try:
        # Check cache first
        cache_key = get_cache_key("semantic_search", q, limit, media_type, difficulty, learning_style,
                                min_duration, max_duration, tags)

        cached_result = cache_get(cache_key)
        if cached_result:
            # Convert back to ResourceSchema format
            result = []
            for item in cached_result:
                resource = db.query(Resource).filter(Resource.id == item['id']).first()
                if resource:
                    result.append(resource)
            return result

        # Prepare filters
        filters = {}
        if media_type:
            filters['media_type'] = media_type
        if difficulty:
            filters['difficulty'] = difficulty
        if learning_style:
            filters['learning_style'] = learning_style
        if min_duration is not None:
            filters['min_duration'] = min_duration
        if max_duration is not None:
            filters['max_duration'] = max_duration
        if tags:
            filters['tags'] = tags

        # Perform semantic search
        search_results = vector_store.search_similar(q, top_k=limit, filters=filters)

        if not search_results:
            # Fallback to basic text search if vector search fails
            return await _fallback_text_search(q, limit, filters, db)

        # Get full resource objects from database
        result = []
        for item in search_results:
            resource = db.query(Resource).filter(Resource.id == item['id']).first()
            if resource:
                result.append(resource)

        # Cache the results (store IDs and scores)
        cache_data = [{'id': r.id, 'score': next((item['similarity_score'] for item in search_results if item['id'] == r.id), 0)} for r in result]
        cache_set(cache_key, cache_data, 1800)  # Cache for 30 minutes

        return result

    except Exception as e:
        # Fallback to text search on error
        return await _fallback_text_search(q, limit, {}, db)


@router.get("/hybrid", response_model=List[ResourceSchema])
async def hybrid_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    use_semantic: bool = Query(True, description="Include semantic search"),
    use_text: bool = Query(True, description="Include text search"),
    semantic_weight: float = Query(0.7, ge=0, le=1, description="Weight for semantic search results"),
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    learning_style: Optional[str] = Query(None, description="Filter by learning style"),
    min_duration: Optional[int] = Query(None, description="Minimum duration in minutes"),
    max_duration: Optional[int] = Query(None, description="Maximum duration in minutes"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Hybrid search combining semantic and traditional text search"""
    try:
        # Prepare filters
        filters = {}
        if media_type:
            filters['media_type'] = media_type
        if difficulty:
            filters['difficulty'] = difficulty
        if learning_style:
            filters['learning_style'] = learning_style
        if min_duration is not None:
            filters['min_duration'] = min_duration
        if max_duration is not None:
            filters['max_duration'] = max_duration
        if tags:
            filters['tags'] = tags

        results = {}

        # Semantic search
        if use_semantic:
            semantic_results = vector_store.search_similar(q, top_k=limit * 2, filters=filters)
            for item in semantic_results:
                resource_id = item['id']
                score = item['similarity_score'] * semantic_weight
                results[resource_id] = {
                    'score': score,
                    'type': 'semantic',
                    'data': item
                }

        # Text search
        if use_text:
            text_results = await _perform_text_search(q, limit * 2, filters, db)
            text_weight = 1.0 - semantic_weight
            for item in text_results:
                resource_id = item.id
                # Calculate text relevance score (simplified)
                title_match = q.lower() in item.title.lower()
                desc_match = item.description and q.lower() in item.description.lower()
                score = (0.7 if title_match else 0.3 if desc_match else 0.1) * text_weight

                if resource_id in results:
                    results[resource_id]['score'] += score
                    results[resource_id]['type'] = 'hybrid'
                else:
                    results[resource_id] = {
                        'score': score,
                        'type': 'text',
                        'resource': item
                    }

        # Sort and limit results
        sorted_results = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
        final_results = []

        for resource_id, result_data in sorted_results[:limit]:
            if 'resource' in result_data:
                final_results.append(result_data['resource'])
            else:
                # Get from database if not already loaded
                resource = db.query(Resource).filter(Resource.id == resource_id).first()
                if resource:
                    final_results.append(resource)

        return final_results

    except Exception as e:
        # Fallback to text search
        return await _fallback_text_search(q, limit, filters if 'filters' in locals() else {}, db)


async def _perform_text_search(query: str, limit: int, filters: dict, db: Session) -> List[Resource]:
    """Perform traditional text search"""
    try:
        # Build query
        search_query = db.query(Resource)

        # Apply text search
        search_term = f"%{query}%"
        search_query = search_query.filter(
            (Resource.title.ilike(search_term)) |
            (Resource.description.ilike(search_term)) |
            (Resource.tags.any(search_term))
        )

        # Apply filters
        if filters.get('media_type'):
            search_query = search_query.filter(Resource.media_type == filters['media_type'])
        if filters.get('difficulty'):
            search_query = search_query.filter(Resource.difficulty == filters['difficulty'])
        if filters.get('learning_style'):
            search_query = search_query.filter(Resource.learning_style == filters['learning_style'])
        if filters.get('min_duration'):
            search_query = search_query.filter(Resource.duration_minutes >= filters['min_duration'])
        if filters.get('max_duration'):
            search_query = search_query.filter(Resource.duration_minutes <= filters['max_duration'])
        if filters.get('tags'):
            search_query = search_query.filter(Resource.tags.overlap(filters['tags']))

        # Order by relevance (simplified)
        search_query = search_query.order_by(Resource.rating.desc(), Resource.rating_count.desc())

        return search_query.limit(limit).all()

    except Exception as e:
        return []


async def _fallback_text_search(query: str, limit: int, filters: dict, db: Session) -> List[Resource]:
    """Fallback text search when semantic search fails"""
    return await _perform_text_search(query, limit, filters, db)


@router.post("/index/rebuild")
async def rebuild_search_index(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rebuild the search index (admin operation)"""
    # TODO: Add admin check
    try:
        # Get all resources
        resources = db.query(Resource).all()

        if not resources:
            return {"message": "No resources to index"}

        # Convert to DataFrame
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

        # Rebuild the index
        vector_store.rebuild_index(resources_df)

        return {
            "message": f"Search index rebuilt successfully with {len(resources)} resources",
            "stats": vector_store.get_stats()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Index rebuild failed: {str(e)}"
        )


@router.get("/stats")
async def get_search_stats():
    """Get search index statistics"""
    return vector_store.get_stats()


@router.get("/suggest")
async def get_search_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Partial search query"),
    limit: int = Query(5, ge=1, le=20, description="Number of suggestions")
):
    """Get search suggestions based on partial query"""
    # This is a simplified implementation
    # In production, you might use:
    # - Query logs analysis
    # - Popular searches
    # - Auto-complete from indexed terms

    suggestions = [
        f"{q} tutorial",
        f"{q} course",
        f"{q} guide",
        f"learn {q}",
        f"{q} examples"
    ]

    return {"suggestions": suggestions[:limit]}