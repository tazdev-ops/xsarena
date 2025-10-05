"""Core engine for LMASudio - handles communication with backends and manages session state."""
import asyncio
import json
import re
from typing import List, Dict, Optional, Callable, Any
from .backends import Backend, Message
from .state import SessionState
from .chunking import build_anchor_prompt, detect_repetition, anti_repeat_filter
from .templates import CONTINUATION_PROMPTS, REPETITION_PROMPTS

class Engine:
    """Main engine that handles communication with backends and manages session state."""
    
    def __init__(self, backend: Backend, state: SessionState):
        self.backend = backend
        self.state = state
        self.tools: Optional[List[Callable]] = None  # For coder mode
        self.redaction_filter: Optional[Callable[[str], str]] = None
    
    async def send_and_collect(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a message and collect the response, handling continuation and repetition."""
        # Build the full message history
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        
        # Add history (respecting window size)
        history_start = max(0, len(self.state.history) - self.state.window_size)
        for msg in self.state.history[history_start:]:
            messages.append(Message(role=msg.role, content=msg.content))
        
        # Add the current user prompt
        messages.append(Message(role="user", content=user_prompt))
        
        # Add continuation context if in anchor mode
        if self.state.continuation_mode == "anchor" and self.state.anchors:
            anchor_text = " ".join(self.state.anchors[-3:])  # Use last 3 anchors
            anchor_prompt = build_anchor_prompt(anchor_text, self.state.anchor_length)
            if anchor_prompt:
                # Append to the last user message or add as a new assistant message
                if messages and messages[-1].role == "user":
                    messages[-1].content += anchor_prompt
                else:
                    messages.append(Message(role="user", content=anchor_prompt))
        
        # Apply redaction filter if enabled
        if self.redaction_filter:
            for msg in messages:
                msg.content = self.redaction_filter(msg.content)
        
        # Send to backend
        response = await self.backend.send(messages)
        
        # Post-process the response
        processed_response = await self.postprocess_response(response)
        
        # Add to history
        self.state.add_message("user", user_prompt)
        self.state.add_message("assistant", processed_response)
        
        # Add to anchors if in anchor mode
        if self.state.continuation_mode == "anchor":
            self.state.add_anchor(processed_response)
        
        return processed_response
    
    async def postprocess_response(self, response: str) -> str:
        """Post-process the response to handle repetition, CF flags, etc."""
        # Check for repetition
        if self.state.history:
            # Simple check against the last response
            last_response = ""
            for msg in reversed(self.state.history):
                if msg.role == "assistant":
                    last_response = msg.content
                    break
            
            if detect_repetition(response, self.state.repetition_threshold):
                # Handle repetition - for now, just return the response, but in the future
                # we might want to implement a retry mechanism
                print("Repetition detected, considering retry...")
                
                # Optional: implement retry with stricter prompt
                if False:  # This could be enabled based on a setting
                    anchor_context = build_anchor_prompt(
                        last_response, 
                        self.state.anchor_length
                    )
                    retry_prompt = REPETITION_PROMPTS["retry"].format(anchor_context=anchor_context)
                    
                    # This would involve sending a new request with the retry prompt
                    # For now, we'll just continue with postprocessing
        
        # Apply anti-repeat filter
        processed = anti_repeat_filter(response, [msg.content for msg in self.state.history if msg.role == "assistant"])
        
        # Strip NEXT tokens or other markers
        processed = re.sub(r'\[\[NEXT\]\]', '', processed)
        processed = processed.strip()
        
        return processed
    
    def set_tools(self, tools: List[Callable]):
        """Set tools for the engine (for coder mode)."""
        self.tools = tools
    
    def set_redaction_filter(self, filter_func: Callable[[str], str]):
        """Set a redaction filter to strip sensitive information."""
        self.redaction_filter = filter_func
    
    async def run_with_tools(self, user_prompt: str) -> str:
        """Run a prompt with tool support (for coder mode)."""
        if not self.tools:
            return await self.send_and_collect(user_prompt)
        
        # For now, this is a simplified implementation
        # In a full implementation, this would handle JSON tool calls
        return await self.send_and_collect(user_prompt)