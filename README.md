# servia-backend
## About ServiaAI

ServiaAI is an AI-powered hotel recruitment platform that transforms 
the way hotels attract, screen, and hire talent. Instead of spending 
hours manually reviewing CVs and coordinating interviews, ServiaAI 
automates the entire hiring process - from the moment a candidate 
applies to the final hiring decision.

Candidates register on the platform, upload their CV, and submit a 
short video introduction. ServiaAI's AI engine instantly analyzes 
each CV, scores it from 0 to 100 based on hospitality-specific 
criteria, and provides personalized feedback directly to the candidate. 
Shortlisted candidates are automatically invited for an AI-assisted 
Google Meet interview where a bot joins silently, transcribes the 
conversation in real time, and suggests follow-up questions to the 
recruiter. After the interview, a full AI report is generated with 
a hiring recommendation.

The result is a faster, fairer, and more data-driven hiring process 
that saves hotel HR teams hours of manual work while ensuring the 
best candidates are identified efficiently.

## Prerequisites
- Python 3.10 or higher
- pip
- Git

## Setup Steps

### 1. Clone the repository
git clone https://github.com/sororatech/servia-backend
cd servia-backend

### 2. Create and activate virtual environment
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

### 3. Install dependencies
pip install -r requirements.txt

### 4. Run database migrations
python manage.py migrate

### 5. Start the development server
python manage.py runserver

## Test Command
Open your browser and go to:
http://localhost:8000

Expected result: Page shows "Hello Sorora Tech"

## Local Development with Docker

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose installed

### 1. Set up environment variables
```bash
cp .env.example .env
```
Edit `.env` and fill in your values (ask a teammate for the shared dev credentials).

### 2. Start services
```bash
docker-compose up -d
```

### 3. Run migrations
```bash
docker-compose exec web python manage.py migrate
```

### 4. View logs
```bash
docker-compose logs -f
```

### 5. Stop services
```bash
docker-compose down
```

### Service URLs
| Service | URL |
|---------|-----|
| Django API | http://localhost:8001 |
| Health check | http://localhost:8001/health/ |
| Redis | localhost:6380 |

---

## Tech Stack
- Python 3.13
- Django 4.2
- Django REST Framework
- PostgreSQL (Supabase — shared dev + production)
- Redis (local Docker for Celery/WebSocket)

## Branch Strategy
- main — production only
- staging — pre-production testing
- develop — integration branch
- feature/xxx — one branch per task

## Team
Sorora Tech — ServiaAI Project

## WebSocket Setup Guide

### Overview
WebSocket implementation for live interview transcripts and real-time dashboard updates.

### What Was Implemented

#### 1. Django Channels Configuration
- Added `channels` and `websocket` to `INSTALLED_APPS`
- Set `ASGI_APPLICATION = 'servia.asgi.application'`
- Configured Redis channel layers in `settings.py`

#### 2. WebSocket Consumers (`websocket/consumers.py`)
- **TestConsumer** (`websocket/consumers.py`) – Simple test endpoint (hello → world)
- **InterviewConsumer** (`apps/interview/consumers.py`) – Production endpoint with authentication and room-based broadcast
  - `connect()` - Accepts connection, authenticates via token, joins interview room
  - `disconnect()` - Removes from room on disconnect
  - `receive()` - Processes incoming messages, broadcasts to room
  - `send()` - Sends messages to clients

#### 3. WebSocket Routing
- Created `servia_backend/routing.py` with WebSocket URL patterns
- Updated `servia_backend/asgi.py` to route WebSocket connections

#### 4. Endpoints
| Endpoint | Purpose | Authentication |
|----------|---------|----------------|
| `ws://localhost:8000/ws/test/` | Test endpoint (hello → world) | None |
| `ws://localhost:8000/ws/interview/{id}/?token={token}` | Interview transcript | Token in query params |

### Installation Steps

#### 1. Install Dependencies
```bash
pip install channels channels-redis daphne
```
#### 2. Start Redis
```bash
docker run -d --name redis-servia -p 6379:6379 redis:alpine
```
#### 3. Verify Redis
```bash
docker exec redis-servia redis-cli ping
# Expected output: PONG
```
#### 4. Run ASGI Server
```bash
daphne -b 127.0.0.1 -p 8000 servia.asgi:application
```

### Testing

#### Using Postman
1. Connect to: `ws://localhost:8000/ws/test/`
2. Send: `{"message": "hello"}`
3. Expected response:
```json
{
    "response": "world",
    "latency_ms": 0.0,
    "original": "hello"
}
```
#### Verification
- Connection successful
- "hello" → "world" response
- Latency <100ms (achieved: 0.0ms)

### File Structure
```
servia-backend/
├── apps/
│   └── interview/
│       └── consumers.py     # InterviewConsumer (with auth, room-based)
├── websocket/
│   └── consumers.py         # TestConsumer only (for testing)
├── servia_backend/
│   ├── asgi.py              # Protocol router
│   ├── routing.py           # WebSocket URL patterns
│   └── settings.py          # Channel layers config
└── requirements.txt         # Project dependencies
```

### Dependencies
- Django 4.2.24
- Django Channels 4.3.2
- channels-redis 4.3.0
- Daphne 4.2.1 (ASGI server)
- Redis 7.3.0

### Notes
- Use Daphne, not `runserver`, for WebSocket support
- Redis must be running before starting Daphne
- Test endpoint responds with latency in milliseconds
- Production endpoints require authentication token
- Test endpoint is unauthenticated for development
```

```
## Cloudflare R2 Setup

### Overview
Cloudflare R2 is used for storing candidate CVs and other documents with zero egress fees.

### Configuration Completed
- **Bucket:** `servia-cv-storage`
- **Access:** Private read via signed URLs, private write
- **CORS:** Configured for frontend uploads
- **Lifecycle:** Auto-delete after 365 days
- **Free tier:** 10GB storage, 1M writes, 10M reads
```