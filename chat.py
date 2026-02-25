from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from db.database import get_db, ChatMessage
from services.ollama_service import stream_chat, generate_structured, check_ollama_status
import json

router = APIRouter()


class MessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[MessageIn]
    trip_id: Optional[int] = None
    model: str = "llama3"
    keep_alive: str = "5m"  # How long to keep model loaded: "5m", "0" to unload, "-1" forever


class StructuredRequest(BaseModel):
    prompt: str
    model: str = "llama3"
    schema: Optional[Dict[str, Any]] = None  # Optional JSON schema for typed output


@router.post("/stream")
async def chat_stream(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Stream AI response via Server-Sent Events (SSE).
    Each event: data: {"token": "..."} or data: {"done": true, "done_reason": "stop"}
    """
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # Persist the user's message
    last_user_msg = next((m for m in reversed(req.messages) if m.role == "user"), None)
    if last_user_msg:
        db_msg = ChatMessage(role="user", content=last_user_msg.content, trip_id=req.trip_id)
        db.add(db_msg)
        db.commit()

    async def generate():
        full_response = ""
        try:
            async for token in stream_chat(messages, model=req.model, keep_alive=req.keep_alive):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Persist assistant response
            if full_response:
                db_resp = ChatMessage(role="assistant", content=full_response, trip_id=req.trip_id)
                db.add(db_resp)
                db.commit()
            yield f"data: {json.dumps({'done': True, 'done_reason': 'stop'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/generate")
async def generate_structured_response(req: StructuredRequest):
    """
    Non-streaming structured generation using Ollama's format parameter.
    Returns guaranteed JSON output — useful for itinerary creation.
    Includes token usage stats from Ollama (prompt_eval_count, eval_count).
    """
    result = await generate_structured(req.prompt, model=req.model, schema=req.schema)
    return result


@router.get("/history/{trip_id}")
def get_chat_history(trip_id: int, db: Session = Depends(get_db)):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.trip_id == trip_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": str(m.created_at)}
        for m in messages
    ]


@router.get("/status")
async def ollama_status():
    """Check Ollama connectivity and list available local models."""
    return await check_ollama_status()
