# CO-006: SSE Streaming Implementation for Tutor

**Priority**: P2 - Medium  
**Type**: Feature  
**Component**: Streaming/SSE  
**Estimated Effort**: 4-5 hours  
**Dependencies**: CO-001

## Objective

Implement Server-Sent Events (SSE) streaming for tutor interactions, providing real-time progressive hint delivery and conversational tutoring experiences.

## Background

The current tutor implementation returns a stream token but lacks the actual SSE endpoint. According to the design docs, we need:
- Progressive markdown/KaTeX content streaming
- Support for concurrent streams (max 2 per user)
- Normalized event protocol (`message.start`, `message.delta`, `message.end`)
- Optional tool suggestions (e.g., test suggestions)

## High-Level Design

### Architecture
```
TutorController
    ├── POST /v1/tutor/messages → Create stream
    ├── GET /v1/tutor/stream → SSE endpoint
    ├── SSE Stream Management
    │   ├── StreamRegistry (Redis)
    │   ├── EventFormatter
    │   └── ContentChunker
    └── LLM Integration
        ├── OpenAI Streaming
        └── Context Management
```

### Event Protocol
```typescript
// SSE Events
{
  event: "message.start",
  data: { stream_id: "uuid", metadata: {...} }
}

{
  event: "message.delta", 
  data: { content: "chunk", type: "markdown" }
}

{
  event: "tool.suggested_tests",
  data: { tests: [...] }
}

{
  event: "message.end",
  data: { total_tokens: 150, finish_reason: "stop" }
}
```

## Implementation Details

### 1. SSE Infrastructure
Create `src/co/streaming/sse.py`:
```python
from fastapi import Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Dict, Any
import json
import asyncio
import uuid
from datetime import datetime

class SSEMessage:
    """SSE-compliant message format"""
    
    def __init__(self, event: str, data: Any, id: str = None):
        self.event = event
        self.data = data
        self.id = id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
    
    def format(self) -> str:
        """Format as SSE message"""
        lines = []
        
        if self.id:
            lines.append(f"id: {self.id}")
        
        if self.event:
            lines.append(f"event: {self.event}")
        
        # Format data (JSON)
        data_json = json.dumps(self.data, ensure_ascii=False)
        for line in data_json.split('\n'):
            lines.append(f"data: {line}")
        
        lines.append("")  # Empty line to end message
        return "\n".join(lines)

class SSEStream:
    """Manages an individual SSE stream"""
    
    def __init__(self, stream_id: str, user_id: str):
        self.stream_id = stream_id
        self.user_id = user_id
        self.queue = asyncio.Queue()
        self.active = True
        self.created_at = datetime.utcnow()
    
    async def send(self, event: str, data: Any):
        """Send event to stream"""
        if self.active:
            message = SSEMessage(event, data)
            await self.queue.put(message)
    
    async def close(self):
        """Close the stream"""
        self.active = False
        await self.send("stream.close", {"reason": "closed"})
    
    async def generate(self) -> AsyncGenerator[str, None]:
        """Generate SSE events"""
        
        # Send initial connection event
        yield SSEMessage("stream.start", {
            "stream_id": self.stream_id,
            "timestamp": self.created_at.isoformat()
        }).format()
        
        while self.active:
            try:
                # Wait for next message with timeout
                message = await asyncio.wait_for(
                    self.queue.get(), 
                    timeout=30.0
                )
                
                yield message.format()
                
                # Check for end conditions
                if message.event == "message.end":
                    break
                    
            except asyncio.TimeoutError:
                # Send keepalive
                yield SSEMessage("ping", {"timestamp": datetime.utcnow().isoformat()}).format()
            except Exception as e:
                # Send error and close
                yield SSEMessage("error", {"message": str(e)}).format()
                break
        
        # Cleanup
        self.active = False

class SSERegistry:
    """Manages active SSE streams"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.streams: Dict[str, SSEStream] = {}
        self.user_streams: Dict[str, set] = {}
    
    async def create_stream(self, user_id: str) -> str:
        """Create new stream for user"""
        
        # Check concurrent limit
        user_stream_count = len(self.user_streams.get(user_id, set()))
        if user_stream_count >= 2:
            raise ValueError("User has reached maximum concurrent streams (2)")
        
        # Generate stream ID
        stream_id = str(uuid.uuid4())
        
        # Create stream
        stream = SSEStream(stream_id, user_id)
        self.streams[stream_id] = stream
        
        # Track user streams
        if user_id not in self.user_streams:
            self.user_streams[user_id] = set()
        self.user_streams[user_id].add(stream_id)
        
        # Store in Redis for multi-instance support
        await self.redis.setex(
            f"stream:{stream_id}",
            3600,  # 1 hour TTL
            json.dumps({
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat()
            })
        )
        
        return stream_id
    
    async def get_stream(self, stream_id: str) -> SSEStream:
        """Get stream by ID"""
        return self.streams.get(stream_id)
    
    async def close_stream(self, stream_id: str):
        """Close and cleanup stream"""
        
        stream = self.streams.get(stream_id)
        if stream:
            await stream.close()
            
            # Cleanup tracking
            user_id = stream.user_id
            if user_id in self.user_streams:
                self.user_streams[user_id].discard(stream_id)
                if not self.user_streams[user_id]:
                    del self.user_streams[user_id]
            
            del self.streams[stream_id]
        
        # Cleanup Redis
        await self.redis.delete(f"stream:{stream_id}")
    
    async def cleanup_expired(self):
        """Remove expired streams"""
        
        cutoff = datetime.utcnow().timestamp() - 3600  # 1 hour ago
        
        expired = []
        for stream_id, stream in self.streams.items():
            if stream.created_at.timestamp() < cutoff:
                expired.append(stream_id)
        
        for stream_id in expired:
            await self.close_stream(stream_id)
```

### 2. Enhanced Tutor Service
Update `src/co/services/tutor_service.py`:
```python
from ..streaming.sse import SSERegistry, SSEStream
from openai import AsyncOpenAI
import json

class TutorService:
    def __init__(self, redis_client):
        self.sse_registry = SSERegistry(redis_client)
        self.openai_client = AsyncOpenAI()
    
    async def create_tutor_stream(
        self,
        user_id: str,
        session_id: str,
        problem_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create new tutor stream"""
        
        try:
            stream_id = await self.sse_registry.create_stream(user_id)
            
            # Store session context
            await self.redis.setex(
                f"tutor_context:{stream_id}",
                3600,
                json.dumps({
                    "session_id": session_id,
                    "problem_id": problem_id,
                    "user_id": user_id,
                    "context": context
                })
            )
            
            return {
                "stream_id": stream_id,
                "stream_url": f"/v1/tutor/stream?token={stream_id}"
            }
            
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e))
    
    async def send_tutor_message(
        self,
        stream_id: str,
        message: str,
        hint_level: int = 1
    ):
        """Send message to tutor and stream response"""
        
        stream = await self.sse_registry.get_stream(stream_id)
        if not stream:
            raise ValueError("Stream not found")
        
        # Get context
        context_data = await self.redis.get(f"tutor_context:{stream_id}")
        if not context_data:
            raise ValueError("Session context not found")
        
        context = json.loads(context_data)
        
        # Build prompt
        prompt = await self._build_tutor_prompt(
            problem_id=context["problem_id"],
            user_message=message,
            hint_level=hint_level,
            session_context=context["context"]
        )
        
        # Start streaming
        await stream.send("message.start", {
            "message_id": str(uuid.uuid4()),
            "hint_level": hint_level
        })
        
        # Stream from OpenAI
        async for chunk in self._stream_openai_response(prompt):
            await stream.send("message.delta", {
                "content": chunk["content"],
                "type": "markdown"
            })
            
            # Check for tool suggestions
            if chunk.get("tool_call"):
                await stream.send("tool.suggested_tests", {
                    "tests": chunk["tool_call"]["tests"]
                })
        
        # End stream
        await stream.send("message.end", {
            "total_tokens": chunk.get("total_tokens", 0),
            "finish_reason": "stop"
        })
    
    async def _build_tutor_prompt(
        self,
        problem_id: str,
        user_message: str,
        hint_level: int,
        session_context: Dict
    ) -> str:
        """Build context-aware tutor prompt"""
        
        # Get problem details
        problem = await self.problem_bank_client.get_problem(problem_id)
        
        # Get submission history
        submissions = session_context.get("submissions", [])
        
        prompt = f"""
You are a coding interview tutor helping with this problem:

{problem['statement']}

Conversation so far:
{self._format_conversation_history(session_context.get('messages', []))}

User's latest submission attempts:
{self._format_submissions(submissions)}

User asks: {user_message}

Guidelines:
- Hint Level {hint_level}: {"Subtle nudge" if hint_level == 1 else "Moderate guidance" if hint_level == 2 else "Explicit direction"}
- Use Socratic method - ask leading questions
- Focus on problem-solving approach, not code
- Encourage thinking about edge cases
- If appropriate, suggest test cases to consider

Format response in markdown. If suggesting tests, use this format:
```tests
[test cases here]
```
"""
        return prompt
    
    async def _stream_openai_response(self, prompt: str):
        """Stream response from OpenAI"""
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            temperature=0.7
        )
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield {
                    "content": chunk.choices[0].delta.content,
                    "total_tokens": getattr(chunk, 'usage', {}).get('total_tokens')
                }
    
    def _format_conversation_history(self, messages: List[Dict]) -> str:
        """Format previous messages"""
        return "\n".join([
            f"{'User' if m['role'] == 'user' else 'Tutor'}: {m['content']}"
            for m in messages[-5:]  # Last 5 messages
        ])
    
    def _format_submissions(self, submissions: List[Dict]) -> str:
        """Format submission history"""
        if not submissions:
            return "No submissions yet."
        
        latest = submissions[-1]
        return f"""
Status: {latest['status']}
Passed: {latest['visible_passed']}/{latest['visible_total']} visible, {latest['hidden_passed']}/{latest['hidden_total']} hidden
Failed categories: {', '.join(latest.get('categories', []))}
"""
```

### 3. SSE Router
Create `src/co/routes/streaming.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from ..services.tutor_service import TutorService
from ..auth import get_current_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/tutor/stream")
async def tutor_stream(
    token: str,
    request: Request,
    tutor_service: TutorService = Depends(get_tutor_service)
):
    """SSE endpoint for tutor streaming"""
    
    # Validate token/stream
    stream = await tutor_service.sse_registry.get_stream(token)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Check if client disconnected
    async def check_disconnect():
        while stream.active:
            if await request.is_disconnected():
                logger.info(f"Client disconnected from stream {token}")
                await tutor_service.sse_registry.close_stream(token)
                break
            await asyncio.sleep(1)
    
    # Start disconnect monitoring in background
    asyncio.create_task(check_disconnect())
    
    # Return SSE stream
    return StreamingResponse(
        stream.generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@router.post("/tutor/messages")
async def send_tutor_message(
    payload: TutorMessageRequest,
    user = Depends(get_current_user),
    tutor_service: TutorService = Depends(get_tutor_service)
):
    """Send message to tutor (creates or uses existing stream)"""
    
    # Create stream if needed
    if not payload.stream_id:
        stream_info = await tutor_service.create_tutor_stream(
            user_id=str(user.id),
            session_id=payload.session_id,
            problem_id=payload.problem_id,
            context=payload.context or {}
        )
        
        # Send initial message
        asyncio.create_task(
            tutor_service.send_tutor_message(
                stream_info["stream_id"],
                payload.message,
                payload.hint_level
            )
        )
        
        return stream_info
    
    else:
        # Use existing stream
        asyncio.create_task(
            tutor_service.send_tutor_message(
                payload.stream_id,
                payload.message,
                payload.hint_level
            )
        )
        
        return {"message": "Sent to existing stream"}

@router.delete("/tutor/stream/{stream_id}")
async def close_tutor_stream(
    stream_id: str,
    user = Depends(get_current_user),
    tutor_service: TutorService = Depends(get_tutor_service)
):
    """Close tutor stream"""
    
    await tutor_service.sse_registry.close_stream(stream_id)
    return {"message": "Stream closed"}
```

### 4. Request/Response Schemas
Create `src/co/schemas/tutor.py`:
```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

class TutorMessageRequest(BaseModel):
    session_id: str
    problem_id: str
    message: str
    hint_level: int = 1
    stream_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class TutorStreamResponse(BaseModel):
    stream_id: str
    stream_url: str
    
class TutorMessageResponse(BaseModel):
    message: str
    stream_id: Optional[str] = None
```

### 5. Frontend Integration Example
```javascript
// Frontend SSE client
class TutorClient {
    constructor(streamUrl) {
        this.eventSource = new EventSource(streamUrl);
        this.messageBuffer = '';
        
        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleEvent(event.type, data);
        };
        
        // Specific event handlers
        this.eventSource.addEventListener('message.start', (e) => {
            this.onMessageStart(JSON.parse(e.data));
        });
        
        this.eventSource.addEventListener('message.delta', (e) => {
            this.onMessageDelta(JSON.parse(e.data));
        });
        
        this.eventSource.addEventListener('message.end', (e) => {
            this.onMessageEnd(JSON.parse(e.data));
        });
        
        this.eventSource.addEventListener('tool.suggested_tests', (e) => {
            this.onSuggestedTests(JSON.parse(e.data));
        });
    }
    
    onMessageStart(data) {
        this.messageBuffer = '';
        this.showTypingIndicator();
    }
    
    onMessageDelta(data) {
        this.messageBuffer += data.content;
        this.updateMessage(this.messageBuffer);
    }
    
    onMessageEnd(data) {
        this.hideTypingIndicator();
        this.finalizeMessage(this.messageBuffer);
    }
    
    onSuggestedTests(data) {
        this.showTestSuggestions(data.tests);
    }
    
    close() {
        this.eventSource.close();
    }
}

// Usage
const tutorClient = new TutorClient('/v1/tutor/stream?token=abc123');
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_sse.py
async def test_sse_message_formatting():
    message = SSEMessage("test.event", {"data": "value"})
    formatted = message.format()
    
    assert "event: test.event" in formatted
    assert "data: {" in formatted

async def test_stream_creation():
    registry = SSERegistry(mock_redis)
    stream_id = await registry.create_stream("user123")
    
    assert stream_id
    stream = await registry.get_stream(stream_id)
    assert stream.user_id == "user123"

async def test_concurrent_stream_limit():
    registry = SSERegistry(mock_redis)
    
    # Create 2 streams (at limit)
    await registry.create_stream("user123")
    await registry.create_stream("user123")
    
    # Third should fail
    with pytest.raises(ValueError):
        await registry.create_stream("user123")
```

### Integration Tests
```python
# tests/integration/test_tutor_streaming.py
async def test_tutor_stream_flow():
    # Create stream
    response = await client.post("/v1/tutor/messages", json={
        "session_id": "sess123",
        "problem_id": "prob123",
        "message": "I need help"
    })
    
    stream_url = response.json()["stream_url"]
    
    # Connect to SSE
    async with aiohttp.ClientSession() as session:
        async with session.get(stream_url) as resp:
            async for line in resp.content:
                if line.startswith(b"event: message.delta"):
                    # Verify we receive content
                    assert b"data:" in line
```

## Performance Considerations

- Limit concurrent streams per user (2)
- Set TTL on stream data in Redis (1 hour)
- Use connection pooling for Redis
- Monitor memory usage of active streams
- Implement graceful degradation if streaming fails

## Success Criteria

- [ ] SSE endpoint returns proper event-stream format
- [ ] Messages stream progressively from LLM
- [ ] Concurrent stream limit enforced (2 per user)
- [ ] Client disconnect detection works
- [ ] Stream cleanup after timeout/disconnect
- [ ] Tool suggestions delivered as separate events
- [ ] Frontend can consume and display streamed content

## Security Considerations

- Validate stream tokens before allowing access
- Rate limit stream creation (5 per minute per user)
- Sanitize all streamed content
- Log streaming access for audit
- Ensure streams are user-scoped

## Notes

- Consider WebSocket upgrade path for bidirectional features
- Monitor streaming performance and latency
- Future: Add typing indicators during generation
- Future: Support audio streaming for voice tutoring