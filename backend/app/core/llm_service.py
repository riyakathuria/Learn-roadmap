"""
LLM Service for roadmap generation and content analysis.
"""

import openai
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

from .config import settings
from .cache import cache_get, cache_set, get_cache_key

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with OpenAI API for roadmap generation"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if self.api_key:
            openai.api_key = self.api_key
        self.model = model
        self.cache_expiry = 3600  # 1 hour

    def _get_cache_key(self, concept: str, duration: int, preferences: Dict) -> str:
        """Generate cache key for LLM requests"""
        key_data = f"{concept}:{duration}:{json.dumps(preferences, sort_keys=True)}"
        return get_cache_key("llm_roadmap", key_data)

    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from LLM response"""
        # Remove markdown code blocks if present
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*$', '', response)

        # Find JSON object
        json_start = response.find('{')
        json_end = response.rfind('}') + 1

        if json_start != -1 and json_end > json_start:
            return response[json_start:json_end]

        return response.strip()

    def generate_roadmap(self, concept: str, duration_weeks: int,
                        user_preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a learning roadmap using LLM"""

        if not self.api_key:
            return self._generate_fallback_roadmap(concept, duration_weeks, user_preferences)

        # Check cache first
        cache_key = self._get_cache_key(concept, duration_weeks, user_preferences or {})
        cached_result = cache_get(cache_key)
        if cached_result:
            return cached_result

        try:
            # Build prompt
            prompt = self._build_roadmap_prompt(concept, duration_weeks, user_preferences)

            # Call OpenAI API
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert educational consultant who creates structured learning roadmaps. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )

            # Extract and parse response
            raw_content = response.choices[0].message.content
            cleaned_content = self._clean_json_response(raw_content)

            roadmap_data = json.loads(cleaned_content)

            # Validate and normalize the response
            normalized_data = self._normalize_roadmap_response(roadmap_data)

            # Cache the result
            cache_set(cache_key, normalized_data, self.cache_expiry)

            return normalized_data

        except Exception as e:
            logger.error(f"LLM roadmap generation failed: {e}")
            return self._generate_fallback_roadmap(concept, duration_weeks, user_preferences)

    def _build_roadmap_prompt(self, concept: str, duration_weeks: int,
                             user_preferences: Optional[Dict[str, Any]] = None) -> str:
        """Build the prompt for roadmap generation"""

        preferences_text = ""
        if user_preferences:
            prefs = []
            if user_preferences.get('learning_style'):
                prefs.append(f"Learning Style: {user_preferences['learning_style']}")
            if user_preferences.get('experience_level'):
                prefs.append(f"Experience Level: {user_preferences['experience_level']}")
            if user_preferences.get('preferred_difficulty'):
                prefs.append(f"Preferred Difficulty: {user_preferences['preferred_difficulty']}")
            if user_preferences.get('preferred_media_types'):
                prefs.append(f"Preferred Media Types: {', '.join(user_preferences['preferred_media_types'])}")
            if prefs:
                preferences_text = f"User Preferences: {'; '.join(prefs)}. "

        prompt = f"""
Create a structured learning roadmap for: {concept}

Duration: {duration_weeks} weeks
{preferences_text}

Please provide a JSON response with the following structure:
{{
  "title": "Descriptive roadmap title",
  "description": "Brief overview of the roadmap",
  "concept": "{concept}",
  "duration_weeks": {duration_weeks},
  "difficulty": "beginner|intermediate|advanced",
  "learning_objectives": ["List 3-5 main learning objectives"],
  "prerequisites": ["List any prerequisites if applicable"],
  "steps": [
    {{
      "title": "Step title",
      "description": "Detailed description of what to learn",
      "order_index": 1,
      "estimated_hours": 10,
      "difficulty": "beginner|intermediate|advanced",
      "prerequisites": ["Any step-specific prerequisites"],
      "learning_objectives": ["What you'll accomplish in this step"],
      "resources_needed": ["Books, tools, or materials needed"],
      "milestones": ["Measurable outcomes for this step"]
    }}
  ],
  "estimated_total_hours": 80,
  "recommended_schedule": "Suggested pace and weekly breakdown",
  "assessment_methods": ["How to measure progress"],
  "common_challenges": ["Potential difficulties learners might face"],
  "tips_for_success": ["Advice for successful completion"]
}}

Ensure the roadmap is realistic for the given time frame and appropriately leveled.
"""

        return prompt

    def _normalize_roadmap_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate LLM response"""
        normalized = {
            "title": data.get("title", f"Learning Roadmap: {data.get('concept', 'Unknown')}"),
            "description": data.get("description", ""),
            "concept": data.get("concept", ""),
            "duration_weeks": data.get("duration_weeks", 8),
            "difficulty": data.get("difficulty", "intermediate"),
            "learning_objectives": data.get("learning_objectives", []),
            "prerequisites": data.get("prerequisites", []),
            "steps": [],
            "estimated_total_hours": data.get("estimated_total_hours", 0),
            "recommended_schedule": data.get("recommended_schedule", ""),
            "assessment_methods": data.get("assessment_methods", []),
            "common_challenges": data.get("common_challenges", []),
            "tips_for_success": data.get("tips_for_success", []),
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": self.model
        }

        # Normalize steps
        steps = data.get("steps", [])
        for i, step in enumerate(steps):
            normalized_step = {
                "title": step.get("title", f"Step {i+1}"),
                "description": step.get("description", ""),
                "order_index": step.get("order_index", i + 1),
                "estimated_hours": step.get("estimated_hours", 8),
                "difficulty": step.get("difficulty", "intermediate"),
                "prerequisites": step.get("prerequisites", []),
                "learning_objectives": step.get("learning_objectives", []),
                "resources_needed": step.get("resources_needed", []),
                "milestones": step.get("milestones", [])
            }
            normalized["steps"].append(normalized_step)

        return normalized

    def _generate_fallback_roadmap(self, concept: str, duration_weeks: int,
                                  user_preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a basic roadmap when LLM is not available"""
        logger.info(f"Generating fallback roadmap for: {concept}")

        # Simple template-based roadmap generation
        difficulty = user_preferences.get('experience_level', 'intermediate') if user_preferences else 'intermediate'

        steps = []
        if difficulty == 'beginner':
            steps = self._get_beginner_steps(concept, duration_weeks)
        elif difficulty == 'intermediate':
            steps = self._get_intermediate_steps(concept, duration_weeks)
        else:
            steps = self._get_advanced_steps(concept, duration_weeks)

        return {
            "title": f"{concept} Learning Roadmap",
            "description": f"A structured {duration_weeks}-week journey to learn {concept}",
            "concept": concept,
            "duration_weeks": duration_weeks,
            "difficulty": difficulty,
            "learning_objectives": [f"Master the fundamentals of {concept}", f"Build practical projects", f"Understand advanced concepts"],
            "prerequisites": ["Basic computer literacy"],
            "steps": steps,
            "estimated_total_hours": len(steps) * 8,
            "recommended_schedule": f"Study {len(steps) // duration_weeks} steps per week",
            "assessment_methods": ["Complete projects", "Take quizzes", "Build portfolio"],
            "common_challenges": ["Time management", "Staying motivated", "Understanding complex concepts"],
            "tips_for_success": ["Practice regularly", "Join communities", "Build projects"],
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": "fallback"
        }

    def _get_beginner_steps(self, concept: str, duration_weeks: int) -> List[Dict[str, Any]]:
        """Generate beginner-level steps"""
        return [
            {
                "title": "Introduction and Setup",
                "description": f"Learn the basics of {concept} and set up your development environment",
                "order_index": 1,
                "estimated_hours": 8,
                "difficulty": "beginner",
                "prerequisites": [],
                "learning_objectives": ["Understand what {concept} is", "Set up development environment"],
                "resources_needed": ["Computer", "Internet connection"],
                "milestones": ["Environment setup complete", "Basic concepts understood"]
            },
            {
                "title": "Core Fundamentals",
                "description": f"Learn the fundamental concepts and syntax of {concept}",
                "order_index": 2,
                "estimated_hours": 12,
                "difficulty": "beginner",
                "prerequisites": ["Step 1"],
                "learning_objectives": ["Master basic syntax", "Understand core concepts"],
                "resources_needed": ["Tutorial resources", "Practice exercises"],
                "milestones": ["Write first program", "Complete basic exercises"]
            },
            {
                "title": "Building Projects",
                "description": "Apply your knowledge by building small projects",
                "order_index": 3,
                "estimated_hours": 16,
                "difficulty": "beginner",
                "prerequisites": ["Step 2"],
                "learning_objectives": ["Apply theoretical knowledge", "Build confidence"],
                "resources_needed": ["Project ideas", "Mentorship"],
                "milestones": ["Complete first project", "Share work with others"]
            }
        ]

    def _get_intermediate_steps(self, concept: str, duration_weeks: int) -> List[Dict[str, Any]]:
        """Generate intermediate-level steps"""
        return [
            {
                "title": "Review and Advanced Fundamentals",
                "description": f"Strengthen your understanding of {concept} fundamentals and explore advanced topics",
                "order_index": 1,
                "estimated_hours": 10,
                "difficulty": "intermediate",
                "prerequisites": ["Basic knowledge"],
                "learning_objectives": ["Review fundamentals", "Learn advanced concepts"],
                "resources_needed": ["Advanced tutorials", "Reference materials"],
                "milestones": ["Complete advanced exercises", "Understand complex topics"]
            },
            {
                "title": "Framework and Tools",
                "description": f"Learn popular frameworks and tools for {concept}",
                "order_index": 2,
                "estimated_hours": 15,
                "difficulty": "intermediate",
                "prerequisites": ["Step 1"],
                "learning_objectives": ["Master frameworks", "Understand best practices"],
                "resources_needed": ["Framework documentation", "Tool setup"],
                "milestones": ["Build with frameworks", "Follow best practices"]
            },
            {
                "title": "Real-world Projects",
                "description": "Build substantial projects that demonstrate your skills",
                "order_index": 3,
                "estimated_hours": 20,
                "difficulty": "intermediate",
                "prerequisites": ["Step 2"],
                "learning_objectives": ["Build complex applications", "Solve real problems"],
                "resources_needed": ["Project requirements", "APIs and services"],
                "milestones": ["Deploy applications", "Handle production issues"]
            }
        ]

    def _get_advanced_steps(self, concept: str, duration_weeks: int) -> List[Dict[str, Any]]:
        """Generate advanced-level steps"""
        return [
            {
                "title": "Deep Dive into Advanced Topics",
                "description": f"Explore advanced and specialized areas of {concept}",
                "order_index": 1,
                "estimated_hours": 15,
                "difficulty": "advanced",
                "prerequisites": ["Strong fundamentals"],
                "learning_objectives": ["Master advanced concepts", "Understand internals"],
                "resources_needed": ["Research papers", "Advanced documentation"],
                "milestones": ["Implement advanced features", "Understand design decisions"]
            },
            {
                "title": "Architecture and Design Patterns",
                "description": f"Learn advanced architectural patterns and design principles for {concept}",
                "order_index": 2,
                "estimated_hours": 18,
                "difficulty": "advanced",
                "prerequisites": ["Step 1"],
                "learning_objectives": ["Design scalable systems", "Apply design patterns"],
                "resources_needed": ["Architecture books", "Case studies"],
                "milestones": ["Design complex systems", "Implement patterns"]
            },
            {
                "title": "Expert Projects and Contributions",
                "description": "Build expert-level projects and contribute to the community",
                "order_index": 3,
                "estimated_hours": 25,
                "difficulty": "advanced",
                "prerequisites": ["Step 2"],
                "learning_objectives": ["Lead projects", "Contribute to open source"],
                "resources_needed": ["Open source projects", "Mentorship opportunities"],
                "milestones": ["Lead development", "Contribute meaningfully to community"]
            }
        ]

    def generate_step_resources(self, step_title: str, step_description: str, concept: str, difficulty: str) -> List[Dict[str, Any]]:
        """Generate 3 curated learning resources for a specific step using LLM"""

        if not self.api_key:
            return self._generate_fallback_step_resources(step_title, step_description, concept, difficulty)

        try:
            prompt = f"""
            Generate exactly 3 high-quality learning resources for the learning step: "{step_title}"

            Step Description: {step_description}
            Overall Concept: {concept}
            Difficulty Level: {difficulty}

            For each resource, provide:
            1. A descriptive title
            2. Brief description (2-3 sentences)
            3. Resource type (video, course, article, book, tutorial, documentation)
            4. Source platform (YouTube, Coursera, Udemy, freeCodeCamp, MDN, official docs, etc.)
            5. URL (real or plausible URL for the resource)
            6. Difficulty level (beginner/intermediate/advanced)
            7. Estimated duration in minutes
            8. Rating (3.0-5.0)
            9. 2-3 relevant tags

            Format as JSON array with exactly 3 objects.
            Focus on reputable, high-quality resources that directly help with this specific learning step.
            """

            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert educational curator. Generate specific, high-quality learning resources for programming and technical topics. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )

            raw_content = response.choices[0].message.content
            cleaned_content = self._clean_json_response(raw_content)

            resources = json.loads(cleaned_content)

            # Validate and normalize the response
            normalized_resources = []
            for i, resource in enumerate(resources[:3]):  # Ensure exactly 3 resources
                normalized = {
                    "id": 1000 + i,  # Temporary IDs for generated resources
                    "title": resource.get("title", f"Resource {i+1}"),
                    "description": resource.get("description", ""),
                    "url": resource.get("url", "#"),
                    "media_type": resource.get("resource_type", "article"),
                    "difficulty": resource.get("difficulty", difficulty),
                    "duration_minutes": resource.get("duration", 60),
                    "rating": resource.get("rating", 4.5),
                    "rating_count": 100,
                    "tags": resource.get("tags", []),
                    "source": resource.get("source", "Online"),
                    "recommendation_score": 0.9,
                    "recommendation_reason": f"AI-curated resource for {step_title}"
                }
                normalized_resources.append(normalized)

            return normalized_resources

        except Exception as e:
            logger.error(f"LLM resource generation failed: {e}")
            return self._generate_fallback_step_resources(step_title, step_description, concept, difficulty)

    def _generate_fallback_step_resources(self, step_title: str, step_description: str, concept: str, difficulty: str) -> List[Dict[str, Any]]:
        """Fallback resource generation when LLM is unavailable"""
        base_resources = [
            {
                "id": 1001,
                "title": f"{step_title} - Official Documentation",
                "description": f"Comprehensive guide and documentation for {step_title.lower()}",
                "url": f"https://docs.{concept.lower()}.org/{step_title.lower().replace(' ', '-')}",
                "media_type": "documentation",
                "difficulty": difficulty,
                "duration_minutes": 90,
                "rating": 4.5,
                "rating_count": 500,
                "tags": [concept.lower(), "documentation"],
                "source": "Official Docs",
                "recommendation_score": 0.8,
                "recommendation_reason": f"Official documentation for {step_title}"
            },
            {
                "id": 1002,
                "title": f"{step_title} Tutorial - Video Series",
                "description": f"Step-by-step video tutorial covering {step_title.lower()} fundamentals and advanced concepts",
                "url": f"https://youtube.com/results?search_query={step_title.lower().replace(' ', '+')}+tutorial",
                "media_type": "video",
                "difficulty": difficulty,
                "duration_minutes": 120,
                "rating": 4.7,
                "rating_count": 1000,
                "tags": [concept.lower(), "tutorial", "video"],
                "source": "YouTube",
                "recommendation_score": 0.85,
                "recommendation_reason": f"Comprehensive video tutorial for {step_title}"
            },
            {
                "id": 1003,
                "title": f"Interactive {step_title} Course",
                "description": f"Hands-on course with exercises and projects for learning {step_title.lower()}",
                "url": f"https://freecodecamp.org/learn/{concept.lower()}-{step_title.lower().replace(' ', '-')}",
                "media_type": "course",
                "difficulty": difficulty,
                "duration_minutes": 180,
                "rating": 4.8,
                "rating_count": 800,
                "tags": [concept.lower(), "interactive", "exercises"],
                "source": "freeCodeCamp",
                "recommendation_score": 0.9,
                "recommendation_reason": f"Interactive course with hands-on exercises for {step_title}"
            }
        ]

        return base_resources


# Global LLM service instance
llm_service = LLMService()