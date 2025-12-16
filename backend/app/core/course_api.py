"""
Coursera Partner API integration for course data.
This module handles fetching course information from Coursera's Partner API.
"""

import httpx
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..core.config import settings

logger = logging.getLogger(__name__)


class CourseraAPIClient:
    """
    Client for interacting with Coursera's Partner API.

    Note: This requires a valid Coursera Partner API key and partnership agreement.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.coursera.org/api/"):
        self.api_key = api_key or settings.COURSERA_API_KEY
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}" if self.api_key else None
            }
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def search_courses(
        self,
        query: str = "",
        limit: int = 20,
        start: int = 0,
        domains: Optional[List[str]] = None,
        language: str = "en",
        product_type: str = "SPECIALIZATION"
    ) -> Dict[str, Any]:
        """
        Search for courses on Coursera.

        Args:
            query: Search query string
            limit: Number of results to return
            start: Starting index for pagination
            domains: List of domain IDs to filter by
            language: Language code (e.g., 'en', 'es')
            product_type: Type of course product ('COURSE', 'SPECIALIZATION', 'PROFESSIONAL_CERTIFICATE')

        Returns:
            Dict containing search results
        """
        params = {
            "q": "search",
            "query": query,
            "limit": limit,
            "start": start,
            "primaryLanguage": language,
            "productType": product_type
        }

        if domains:
            params["domainIds"] = ",".join(domains)

        try:
            response = await self.client.get(
                f"{self.base_url}partners/v1/courses",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Coursera API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error searching Coursera courses: {str(e)}")
            raise

    async def get_course_details(self, course_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific course.

        Args:
            course_id: Coursera course ID

        Returns:
            Dict containing course details
        """
        try:
            response = await self.client.get(
                f"{self.base_url}partners/v1/courses/{course_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Coursera API error for course {course_id}: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting course details for {course_id}: {str(e)}")
            raise

    async def get_course_content(self, course_id: str) -> Dict[str, Any]:
        """
        Get course content information including modules and lectures.

        Args:
            course_id: Coursera course ID

        Returns:
            Dict containing course content
        """
        try:
            response = await self.client.get(
                f"{self.base_url}partners/v1/courses/{course_id}/content"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Coursera API error for course content {course_id}: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting course content for {course_id}: {str(e)}")
            raise


class CourseDataProcessor:
    """
    Processes Coursera course data into our internal resource format.
    """

    @staticmethod
    def process_course_data(course_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Coursera course data to our internal resource format.

        Args:
            course_data: Raw course data from Coursera API

        Returns:
            Processed resource data
        """
        try:
            # Extract basic information
            course = course_data.get("elements", [{}])[0] if "elements" in course_data else course_data

            # Map difficulty levels
            difficulty_map = {
                "BEGINNER": "beginner",
                "INTERMEDIATE": "intermediate",
                "ADVANCED": "advanced"
            }

            # Calculate duration in minutes (assuming 4 weeks average if not specified)
            duration_weeks = course.get("workload", {}).get("courseWorkloadEnum", "MODERATE")
            duration_map = {
                "LIGHT": 4,  # weeks
                "MODERATE": 6,
                "HEAVY": 8
            }
            duration_minutes = duration_map.get(duration_weeks, 6) * 7 * 60  # Convert weeks to minutes

            # Extract tags/domains
            domains = course.get("domainTypes", [])
            tags = [domain.get("domainId", "") for domain in domains if domain.get("domainId")]

            # Build resource data
            resource_data = {
                "title": course.get("name", "Unknown Course"),
                "description": course.get("description", ""),
                "url": f"https://www.coursera.org/learn/{course.get('slug', '')}",
                "media_type": "course",
                "difficulty": difficulty_map.get(course.get("level", "BEGINNER"), "beginner"),
                "duration_minutes": duration_minutes,
                "rating": course.get("ratings", {}).get("averageFiveStarRating", 0.0),
                "rating_count": course.get("ratings", {}).get("totalFiveStarRatings", 0),
                "tags": tags,
                "prerequisites": [],  # Would need additional API calls or parsing
                "learning_style": "mixed",  # Default assumption
                "source": "coursera",
                "external_id": course.get("id", ""),
                "metadata": {
                    "coursera_id": course.get("id"),
                    "slug": course.get("slug"),
                    "instructor_names": [inst.get("name", "") for inst in course.get("instructorIds", [])],
                    "partner_name": course.get("partnerIds", [{}])[0].get("name", "") if course.get("partnerIds") else "",
                    "certificate_type": course.get("certificateType", ""),
                    "enrollment_type": course.get("enrollmentType", ""),
                    "session_dates": course.get("sessionDates", {}),
                    "photo_url": course.get("photoUrl", ""),
                    "workload": course.get("workload", {})
                },
                "scraped_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            return resource_data

        except Exception as e:
            logger.error(f"Error processing course data: {str(e)}")
            raise

    @staticmethod
    def extract_course_topics(course_data: Dict[str, Any]) -> List[str]:
        """
        Extract topic keywords from course data for better matching.

        Args:
            course_data: Raw course data from Coursera API

        Returns:
            List of topic keywords
        """
        topics = []

        course = course_data.get("elements", [{}])[0] if "elements" in course_data else course_data

        # Add domain topics
        domains = course.get("domainTypes", [])
        for domain in domains:
            if domain.get("domainId"):
                topics.append(domain["domainId"].lower().replace("-", " "))

        # Add skills from description or other fields
        description = course.get("description", "").lower()
        # Simple keyword extraction - in production, use NLP
        common_topics = [
            "python", "java", "javascript", "machine learning", "data science",
            "web development", "database", "algorithms", "computer science",
            "statistics", "mathematics", "physics", "chemistry", "biology"
        ]

        for topic in common_topics:
            if topic in description:
                topics.append(topic)

        return list(set(topics))  # Remove duplicates


async def fetch_coursera_courses(
    query: str = "",
    limit: int = 50,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    High-level function to fetch and process courses from Coursera.

    Args:
        query: Search query
        limit: Number of courses to fetch
        api_key: Coursera API key (optional, uses settings if not provided)

    Returns:
        List of processed course resources
    """
    courses = []

    try:
        async with CourseraAPIClient(api_key) as client:
            # Search for courses
            search_results = await client.search_courses(
                query=query,
                limit=limit,
                product_type="COURSE"  # Focus on individual courses
            )

            # Process each course
            for course_item in search_results.get("elements", []):
                try:
                    course_id = course_item.get("id")
                    if course_id:
                        # Get detailed course information
                        course_details = await client.get_course_details(course_id)

                        # Process into our format
                        processed_course = CourseDataProcessor.process_course_data(course_details)

                        # Add additional topics
                        topics = CourseDataProcessor.extract_course_topics(course_details)
                        processed_course["tags"].extend(topics)
                        processed_course["tags"] = list(set(processed_course["tags"]))

                        courses.append(processed_course)

                except Exception as e:
                    logger.warning(f"Failed to process course {course_item.get('id')}: {str(e)}")
                    continue

    except Exception as e:
        logger.error(f"Error fetching courses from Coursera: {str(e)}")
        raise

    return courses