# servia-backend
Django REST Framework API for ServiaAI

## WebSocket Setup Guide

### Overview
WebSocket implementation for live interview transcripts and real-time dashboard updates.

### What Was Implemented

#### 1. Django Channels Configuration
- Added `channels` and `websocket` to `INSTALLED_APPS`
- Set `ASGI_APPLICATION = 'servia.asgi.application'`
- Configured Redis channel layers in `settings.py`

#### 2. WebSocket Consumer (`websocket/consumers.py`)
- `connect()` - Accepts WebSocket connections
- `disconnect()` - Handles disconnections
- `receive()` - Processes incoming messages
- `send()` - Sends responses to clients

#### 3. WebSocket Routing
- Created `websocket/routing.py` with WebSocket URL patterns
- Updated `servia/asgi.py` to route WebSocket connections

#### 4. Test Endpoint
- URL: `ws://localhost:8000/ws/test/`
- Sends "world" when receiving "hello"
- Latency measured and returned to client

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
├── servia/
│   ├── asgi.py          # WebSocket routing configuration
│   └── settings.py      # Channel layers and app config
├── websocket/
│   ├── consumers.py     # WebSocket handlers (connect, disconnect, receive, send)
│   └── routing.py       # WebSocket URL patterns
└── requirements.txt     # Project dependencies
```

### Dependencies
- Django 6.0.3
- Django Channels 4.3.2
- channels-redis 4.3.0
- Daphne 4.2.1 (ASGI server)
- Redis 7.3.0

### Notes
- Use Daphne, not `runserver`, for WebSocket support
- Redis must be running before starting Daphne
- Test endpoint responds with latency in milliseconds
```