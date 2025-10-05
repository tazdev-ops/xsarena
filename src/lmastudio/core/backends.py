"""Backend implementations for LMASudio."""
import asyncio
import aiohttp
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Message:
    """A chat message."""
    role: str
    content: str

class Backend(ABC):
    """Abstract base class for backends."""
    
    @abstractmethod
    async def send(self, messages: List[Message], stream: bool = False) -> str:
        """Send messages to the backend and return the response."""
        pass

class BridgeBackend(Backend):
    """Backend that communicates with the local bridge server."""
    
    def __init__(self, base_url: str = "http://localhost:8080/v1"):
        self.base_url = base_url
        self.session_id = None
    
    async def send(self, messages: List[Message], stream: bool = False) -> str:
        """Send messages to the bridge server."""
        async with aiohttp.ClientSession() as session:
            # First, we need to push the messages to the server
            data = {
                "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
                "stream": stream
            }
            
            # Wait for response from the bridge (this would use the polling mechanism)
            # In the actual implementation, this would interact with your CSP-safe polling system
            async with session.post(f"{self.base_url}/chat/completions", json=data) as response:
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")

class OpenRouterBackend(Backend):
    """Backend that communicates directly with OpenRouter."""
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
    
    async def send(self, messages: List[Message], stream: bool = False) -> str:
        """Send messages to OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "stream": stream
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/chat/completions", headers=headers, json=data) as response:
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def estimate_cost(self, messages: List[Message]) -> Dict[str, float]:
        """Estimate the token usage and cost."""
        # Rough estimation based on character count
        total_chars = sum(len(msg.content) for msg in messages)
        input_tokens = total_chars // 4  # Rough estimate: 1 token ~ 4 chars
        output_tokens = 2048  # Estimated max response tokens
        
        # Pricing example (would need to be updated with actual OpenRouter prices)
        input_cost_per_token = 0.00001  # Example: $0.01 per 1K input tokens
        output_cost_per_token = 0.00003  # Example: $0.03 per 1K output tokens
        
        estimated_cost = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": (input_tokens * input_cost_per_token) + (output_tokens * output_cost_per_token)
        }
        
        return estimated_cost

# Backend factory
def create_backend(backend_type: str, **kwargs) -> Backend:
    """Factory function to create the appropriate backend."""
    if backend_type == "bridge":
        return BridgeBackend(base_url=kwargs.get("base_url", "http://localhost:8080/v1"))
    elif backend_type == "openrouter":
        return OpenRouterBackend(
            api_key=kwargs["api_key"], 
            model=kwargs.get("model", "openai/gpt-4o")
        )
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")