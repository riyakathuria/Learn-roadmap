"""
Script to populate the resources table with sample learning resources.
This will fix the empty recommended resources issue.
"""

from app.core.database import get_db
from app.models.resource import Resource
import pandas as pd

def populate_resources():
    """Populate resources table with sample learning resources."""

    resources_data = [
        {
            'title': 'Python for Beginners - Full Course',
            'description': 'Complete Python programming course for absolute beginners. Learn variables, loops, functions, and object-oriented programming.',
            'url': 'https://www.youtube.com/watch?v=_uQrJ0TkZlc',
            'media_type': 'video',
            'difficulty': 'beginner',
            'duration_minutes': 480,
            'rating': 4.8,
            'rating_count': 1250,
            'tags': ['python', 'programming', 'beginner'],
            'prerequisites': [],
            'learning_style': 'visual',
            'source': 'youtube'
        },
        {
            'title': 'JavaScript Fundamentals',
            'description': 'Master JavaScript basics including ES6 features, asynchronous programming, and DOM manipulation.',
            'url': 'https://www.udemy.com/course/javascript-fundamentals/',
            'media_type': 'course',
            'difficulty': 'beginner',
            'duration_minutes': 360,
            'rating': 4.6,
            'rating_count': 890,
            'tags': ['javascript', 'web-development', 'frontend'],
            'prerequisites': ['basic-programming'],
            'learning_style': 'visual',
            'source': 'udemy'
        },
        {
            'title': 'Data Structures and Algorithms in Python',
            'description': 'Comprehensive guide to data structures and algorithms with Python implementations.',
            'url': 'https://www.coursera.org/learn/data-structures-algorithms',
            'media_type': 'course',
            'difficulty': 'intermediate',
            'duration_minutes': 600,
            'rating': 4.9,
            'rating_count': 2100,
            'tags': ['python', 'data-structures', 'algorithms'],
            'prerequisites': ['python-basics'],
            'learning_style': 'reading',
            'source': 'coursera'
        },
        {
            'title': 'Machine Learning with Python',
            'description': 'Learn machine learning concepts and implement models using scikit-learn and TensorFlow.',
            'url': 'https://www.edx.org/course/machine-learning-with-python',
            'media_type': 'course',
            'difficulty': 'intermediate',
            'duration_minutes': 720,
            'rating': 4.7,
            'rating_count': 1540,
            'tags': ['machine-learning', 'python', 'ai'],
            'prerequisites': ['python', 'statistics'],
            'learning_style': 'visual',
            'source': 'edx'
        },
        {
            'title': 'React.js Complete Guide',
            'description': 'Build modern web applications with React.js, including hooks, context, and advanced patterns.',
            'url': 'https://react.dev/learn',
            'media_type': 'course',
            'difficulty': 'intermediate',
            'duration_minutes': 540,
            'rating': 4.8,
            'rating_count': 3200,
            'tags': ['react', 'javascript', 'frontend'],
            'prerequisites': ['javascript', 'html', 'css'],
            'learning_style': 'interactive',
            'source': 'react'
        },
        {
            'title': 'Advanced Python Programming',
            'description': 'Deep dive into advanced Python topics including decorators, metaclasses, and performance optimization.',
            'url': 'https://realpython.com/advanced-python/',
            'media_type': 'article',
            'difficulty': 'advanced',
            'duration_minutes': 180,
            'rating': 4.5,
            'rating_count': 780,
            'tags': ['python', 'advanced', 'programming'],
            'prerequisites': ['python-intermediate'],
            'learning_style': 'reading',
            'source': 'realpython'
        },
        {
            'title': 'Database Design and SQL',
            'description': 'Learn database design principles, normalization, and advanced SQL queries.',
            'url': 'https://www.khanacademy.org/computing/computer-programming/sql',
            'media_type': 'course',
            'difficulty': 'beginner',
            'duration_minutes': 240,
            'rating': 4.3,
            'rating_count': 650,
            'tags': ['sql', 'database', 'data'],
            'prerequisites': [],
            'learning_style': 'interactive',
            'source': 'khanacademy'
        },
        {
            'title': 'Docker for Developers',
            'description': 'Master containerization with Docker for development and deployment workflows.',
            'url': 'https://docker-curriculum.com/',
            'media_type': 'course',
            'difficulty': 'intermediate',
            'duration_minutes': 300,
            'rating': 4.6,
            'rating_count': 920,
            'tags': ['docker', 'devops', 'containers'],
            'prerequisites': ['linux-basics'],
            'learning_style': 'hands-on',
            'source': 'docker'
        },
        {
            'title': 'Git and Version Control',
            'description': 'Complete guide to Git version control system for software development.',
            'url': 'https://git-scm.com/book/en/v2',
            'media_type': 'book',
            'difficulty': 'beginner',
            'duration_minutes': 420,
            'rating': 4.7,
            'rating_count': 1100,
            'tags': ['git', 'version-control', 'development'],
            'prerequisites': [],
            'learning_style': 'reading',
            'source': 'git'
        },
        {
            'title': 'REST API Design and Development',
            'description': 'Learn to design and build RESTful APIs with proper authentication and documentation.',
            'url': 'https://restfulapi.net/',
            'media_type': 'article',
            'difficulty': 'intermediate',
            'duration_minutes': 120,
            'rating': 4.4,
            'rating_count': 580,
            'tags': ['api', 'rest', 'backend'],
            'prerequisites': ['programming-basics'],
            'learning_style': 'reading',
            'source': 'restfulapi'
        }
    ]

    db = next(get_db())

    try:
        # Check if resources already exist
        existing_count = db.query(Resource).count()
        if existing_count > 0:
            print(f"Resources table already has {existing_count} records. Skipping population.")
            return

        # Add resources to database
        for resource_data in resources_data:
            resource = Resource(**resource_data)
            db.add(resource)

        db.commit()
        print(f"Successfully populated resources table with {len(resources_data)} sample resources.")

    except Exception as e:
        db.rollback()
        print(f"Error populating resources: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    populate_resources()