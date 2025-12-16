# Backend Plan (FastAPI)

## API Endpoints

### Authentication Endpoints
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/logout` - User logout
- `GET /auth/me` - Get current user info
- `POST /auth/refresh` - Refresh access token

### Roadmap Endpoints
- `POST /roadmaps/generate` - Generate new roadmap
  - Request: `{concept: string, duration: number, preferences: object}`
  - Response: `{roadmap: Roadmap, recommendations: Resource[]}`
- `GET /roadmaps/{id}` - Get roadmap by ID
- `GET /roadmaps/user/{user_id}` - Get user's roadmaps
- `PUT /roadmaps/{id}/progress` - Update roadmap progress
  - Request: `{step_id: string, completed: boolean, rating: number}`
- `DELETE /roadmaps/{id}` - Delete roadmap

### Resource Endpoints
- `GET /resources/search` - Search resources
  - Query params: `q=query&filters={}&sort=field&order=asc|desc`
- `GET /resources/{id}` - Get resource details
- `POST /resources/{id}/rate` - Rate a resource
  - Request: `{rating: number, review: string?}`
- `POST /resources/{id}/complete` - Mark resource as completed
- `GET /resources/recommendations/{user_id}` - Get personalized recommendations
- `POST /resources/scrape` - Trigger resource scraping (admin only)

### User Endpoints
- `GET /users/{id}` - Get user profile
- `PUT /users/{id}` - Update user profile
- `GET /users/{id}/preferences` - Get user preferences
- `PUT /users/{id}/preferences` - Update user preferences
- `GET /users/{id}/history` - Get user learning history

## Database Schema

### Tables

#### users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    learning_style VARCHAR(50), -- visual, auditory, kinesthetic, reading
    experience_level VARCHAR(50), -- beginner, intermediate, advanced
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### roadmaps
```sql
CREATE TABLE roadmaps (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    concept VARCHAR(255) NOT NULL,
    duration_weeks INTEGER NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, completed, archived
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### roadmap_steps
```sql
CREATE TABLE roadmap_steps (
    id SERIAL PRIMARY KEY,
    roadmap_id INTEGER REFERENCES roadmaps(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL,
    estimated_hours INTEGER,
    difficulty VARCHAR(50), -- beginner, intermediate, advanced
    prerequisites TEXT[],
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### resources
```sql
CREATE TABLE resources (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(500) NOT NULL,
    media_type VARCHAR(50) NOT NULL, -- video, article, course, book, podcast, etc.
    difficulty VARCHAR(50), -- beginner, intermediate, advanced
    duration_minutes INTEGER,
    rating DECIMAL(3,2) DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    tags TEXT[],
    prerequisites TEXT[],
    learning_style VARCHAR(50), -- visual, auditory, kinesthetic, reading
    source VARCHAR(100), -- platform name
    scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### step_resources
```sql
CREATE TABLE step_resources (
    id SERIAL PRIMARY KEY,
    step_id INTEGER REFERENCES roadmap_steps(id) ON DELETE CASCADE,
    resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE,
    is_recommended BOOLEAN DEFAULT true,
    order_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### user_resource_interactions
```sql
CREATE TABLE user_resource_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL, -- view, like, rate, complete, save
    rating INTEGER, -- 1-5 stars
    review TEXT,
    time_spent_minutes INTEGER,
    completed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, resource_id, interaction_type)
);
```

#### user_preferences
```sql
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    preferred_media_types TEXT[], -- preferred resource types
    preferred_difficulty VARCHAR(50),
    preferred_learning_style VARCHAR(50),
    max_duration_minutes INTEGER,
    avoid_tags TEXT[], -- tags to avoid
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Data Flow

### Roadmap Generation Flow
1. User submits concept and duration via POST /roadmaps/generate
2. Validate input and authenticate user
3. Call LLM service to generate roadmap structure
4. Create roadmap record in database
5. Generate step records for the roadmap
6. Call recommendation engine to suggest resources for each step
7. Associate recommended resources with steps
8. Return complete roadmap with recommendations

### Recommendation Flow
1. User requests recommendations via GET /resources/recommendations/{user_id}
2. Retrieve user preferences and interaction history
3. Call hybrid recommendation engine
4. Content-based filtering: Find similar resources based on user preferences
5. Collaborative filtering: Find resources liked by similar users
6. Combine and rank recommendations using hybrid scoring
7. Cache results for performance
8. Return personalized recommendations

### Resource Interaction Flow
1. User rates/completes a resource via POST /resources/{id}/rate or /complete
2. Update user_resource_interactions table
3. Recalculate resource aggregate ratings if applicable
4. Invalidate relevant recommendation caches
5. Update user preference models if needed

## Performance Considerations

### Indexing
- Composite indexes on frequently queried columns
- Full-text search indexes for resource titles and descriptions
- GIN indexes for array columns (tags, prerequisites)

### Caching
- Redis for API response caching
- Cache recommendation results with TTL
- Cache user preferences and profiles

### Background Tasks
- Resource scraping as async tasks
- Model retraining for recommendations
- Data cleanup and maintenance jobs