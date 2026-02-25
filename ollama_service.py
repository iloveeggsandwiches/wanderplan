import httpx
import json
from typing import AsyncGenerator, List, Dict, Optional

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"

SYSTEM_PROMPT = """You are WanderPlan, an expert AI travel planning assistant. You help users plan trips, create detailed itineraries, discover hidden gems, and get practical travel advice.

When a user asks about a destination, you should:
1. Suggest must-see attractions and hidden gems
2. Recommend local food and restaurants
3. Provide practical tips (weather, transport, safety, costs)
4. Help build day-by-day itineraries
5. Suggest accommodations for different budgets

When creating itineraries, format activities as JSON blocks when explicitly requested, like:
```json
{"type": "itinerary", "days": [{"day": 1, "activities": [...]}]}
```

Be enthusiastic, specific, and practical. Always tailor advice to the user's interests and travel style."""


async def stream_chat(
    messages: List[Dict],
    model: str = DEFAULT_MODEL,
    keep_alive: str = "5m",
) -> AsyncGenerator[str, None]:
    """
    Stream a chat response from Ollama.
    Yields text tokens as they arrive.
    Based on POST /api/chat — https://docs.ollama.com/api/chat
    """
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream": True,
        "keep_alive": keep_alive,  # Keep model loaded in memory between requests
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Each streaming chunk has message.content with the next token
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    # done_reason can be: "stop", "length", "load", etc.
                    if data.get("done") and data.get("done_reason") in ("stop", "length"):
                        break
                except json.JSONDecodeError:
                    continue


async def generate_structured(
    prompt: str,
    model: str = DEFAULT_MODEL,
    schema: Optional[Dict] = None,
) -> Dict:
    """
    Generate a structured JSON response (non-streaming).
    Uses format='json' or a JSON schema for guaranteed structured output.
    Useful for itinerary generation.
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": schema if schema else "json",  # Pass full JSON schema or just "json"
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "{}")
        # Surface token usage from response
        usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_duration_ms": round(data.get("total_duration", 0) / 1_000_000),
        }
        try:
            return {"result": json.loads(content), "usage": usage}
        except json.JSONDecodeError:
            return {"result": content, "usage": usage}


async def get_available_models() -> List[str]:
    """List all locally available Ollama models via GET /api/tags."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


async def check_ollama_status() -> Dict:
    """Check if Ollama is running and return available models."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            models = response.json().get("models", [])
            return {
                "running": True,
                "models": [m["name"] for m in models],
                "model_count": len(models),
            }
    except Exception:
        return {"running": False, "models": [], "model_count": 0}
