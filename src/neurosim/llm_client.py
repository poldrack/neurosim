# src/neurosim/llm_client.py
import json
import os
from collections.abc import AsyncIterator

import httpx

API_URL = "https://aiapi-prod.stanford.edu/v1/chat/completions"
DEFAULT_MODEL = "claude-4-5-sonnet"


async def stream_chat(
    messages: list[dict],
    system_prompt: str,
    model: str = DEFAULT_MODEL,
) -> AsyncIterator[str]:
    """Stream chat completion tokens from the Stanford AI API Gateway.

    Yields individual token strings as they arrive.
    """
    api_key = os.environ.get("STANFORD_API_KEY", "")
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    payload = {
        "model": model,
        "stream": True,
        "messages": full_messages,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", API_URL, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                chunk = json.loads(data_str)
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
