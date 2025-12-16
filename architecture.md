# System Architecture

```mermaid
graph TB
    subgraph "User Interface Layer"
        UI[React Frontend with Shadcn UI]
        UI --> API[FastAPI Backend]
    end

    subgraph "API Layer"
        API --> Auth[Authentication Module]
        API --> Roadmap[Roadmap Generator]
        API --> RecSys[Recommendation System]
    end

    subgraph "Recommendation System"
        RecSys --> Content[Content-Based Filtering]
        RecSys --> Collab[Collaborative Filtering]
        RecSys --> Hybrid[Hybrid Engine]
    end

    subgraph "Data Layer"
        DB[(Database: PostgreSQL)]
        Cache[(Redis Cache)]
        VectorDB[(Vector Database for Embeddings)]
    end

    subgraph "External Services"
        WebScraper[Web Scraping Module]
        CourseAPI[Course Database API]
        LLM[Large Language Model for Roadmap Generation]
    end

    Auth --> DB
    Roadmap --> DB
    RecSys --> DB
    RecSys --> Cache
    RecSys --> VectorDB

    Content --> VectorDB
    Collab --> DB

    WebScraper --> DB
    CourseAPI --> DB

    Roadmap --> LLM

    style UI fill:#e1f5fe
    style API fill:#f3e5f5
    style RecSys fill:#e8f5e8
    style DB fill:#fff3e0
    style Cache fill:#fff3e0
    style VectorDB fill:#fff3e0
```

## Component Descriptions

### User Interface Layer
- **React Frontend**: Built with Shadcn UI components for modern, responsive design
- Handles user input for concepts to learn and duration preferences
- Displays generated roadmaps and recommended resources

### API Layer
- **FastAPI Backend**: Provides RESTful APIs for all system operations
- **Authentication Module**: User management and session handling
- **Roadmap Generator**: Processes user input to create step-by-step learning paths
- **Recommendation System**: Core ML-based recommendation engine

### Recommendation System
- **Content-Based Filtering**: Recommends resources based on:
  - Difficulty level
  - Prerequisites
  - Learning style
  - Tags
  - Ratings
  - Media type
- **Collaborative Filtering**: Uses user ratings and completion status for similarity-based recommendations
- **Hybrid Engine**: Combines both approaches for optimal recommendations

### Data Layer
- **PostgreSQL**: Main database for user data, roadmaps, resources, and interactions
- **Redis Cache**: Caches frequently accessed recommendations and user sessions
- **Vector Database**: Stores embeddings for content-based similarity calculations

### External Services
- **Web Scraping Module**: Collects learning resources from various online platforms
- **Course Database API**: Integrates with external course databases (if available)
- **LLM**: Uses large language models to generate personalized roadmaps based on user input

## Data Flow

1. User inputs concept and duration through React frontend
2. Frontend sends request to FastAPI backend
3. Backend processes input and generates roadmap using LLM
4. Recommendation system analyzes user preferences and generates resource suggestions
5. Results are cached and returned to frontend for display
6. User interactions (ratings, completion status) are stored for future recommendations