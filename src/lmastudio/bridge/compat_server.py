"""OpenAI-compatible HTTP API server for LMASudio."""
import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import uvicorn

from ..core.config import Config
from ..core.state import SessionState
from ..core.backends import create_backend
from ..core.engine import Engine

app = FastAPI(title="LMASudio API", version="0.1.0")

# Global engine instance
engine: Optional[Engine] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None
    stop: Optional[List[str]] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Dict[str, int]

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "lmastudio"

class ListModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]

def verify_api_key(authorization: str = Header(None)):
    """Verify API key if required."""
    api_key = os.getenv("LMASTUDIO_API_KEY")
    if api_key and authorization != f"Bearer {api_key}":
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.on_event('startup')
async def startup_event():
    """Initialize the global engine on startup."""
    global engine
    
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, 
                           base_url=config.base_url, 
                           api_key=config.api_key, 
                           model=config.model)
    engine = Engine(backend, state)

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: str = Depends(verify_api_key)
):
    """Handle chat completion requests compatible with OpenAI API."""
    global engine
    
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    
    try:
        # Convert messages to the format our engine expects
        user_message = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
        
        # For now, use the first message as the primary input
        # In a full implementation, we'd process the full message history properly
        primary_message = request.messages[-1].content if request.messages else "Hello"
        
        # Use the configured system prompt or create one based on earlier messages
        system_prompt = None
        for msg in request.messages:
            if msg.role == "system":
                system_prompt = msg.content
                break
        
        # Get response from our engine
        response_text = await engine.send_and_collect(primary_message, system_prompt)
        
        # Create response in OpenAI-compatible format
        import time
        response = ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=response_text
                    )
                )
            ],
            usage={
                "prompt_tokens": len(str(request.messages)),
                "completion_tokens": len(response_text),
                "total_tokens": len(str(request.messages)) + len(response_text)
            }
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models", response_model=ListModelsResponse)
async def list_models(authorization: str = Depends(verify_api_key)):
    """List available models from models.json."""
    try:
        with open("models.json", "r") as f:
            models_data = json.load(f)
    except FileNotFoundError:
        # Default models if models.json doesn't exist
        models_data = {
            "models": [
                {"id": "default", "name": "Default Model", "type": "text"},
                {"id": "gpt-4", "name": "GPT-4", "type": "text"},
                {"id": "claude-3", "name": "Claude 3", "type": "text"}
            ]
        }
    
    models = [
        ModelInfo(id=model["id"]) 
        for model in models_data.get("models", [])
    ]
    
    return ListModelsResponse(data=models)

def main():
    """Run the compatibility server with configurable port."""
    import argparse, os
    parser = argparse.ArgumentParser(description="LMASudio OpenAI-Compatible API Server")
    parser.add_argument("--port", "-p", type=int, default=int(os.getenv("LMA_COMPAT_PORT", "8000")), help="Local API server port (default from LMA_COMPAT_PORT or 8000)")
    parser.add_argument("--host", default=os.getenv("LMA_HOST", "127.0.0.1"), help="Local API server host (default 127.0.0.1)")
    args = parser.parse_args()
    
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()