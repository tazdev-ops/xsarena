"""Session state management for LMASudio."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json
import os
from datetime import datetime

@dataclass
class Message:
    """A chat message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class SessionState:
    """Current session state."""
    history: List[Message] = field(default_factory=list)
    anchors: List[str] = field(default_factory=list)
    continuation_mode: str = "anchor"
    anchor_length: int = 300
    repetition_threshold: float = 0.8
    backend: str = "bridge"
    model: str = "default"
    window_size: int = 100
    current_job_id: Optional[str] = None
    job_queue: List[Dict] = field(default_factory=list)
    settings: Dict = field(default_factory=dict)
    
    def add_message(self, role: str, content: str):
        """Add a message to the history."""
        self.history.append(Message(role=role, content=content))
    
    def add_anchor(self, text: str):
        """Add an anchor to the session."""
        self.anchors.append(text[-self.anchor_length:])
    
    def save_to_file(self, filepath: str):
        """Save state to a JSON file."""
        state_dict = {
            'history': [{'role': m.role, 'content': m.content, 'timestamp': m.timestamp.isoformat()} 
                        for m in self.history],
            'anchors': self.anchors,
            'continuation_mode': self.continuation_mode,
            'anchor_length': self.anchor_length,
            'repetition_threshold': self.repetition_threshold,
            'backend': self.backend,
            'model': self.model,
            'window_size': self.window_size,
            'current_job_id': self.current_job_id,
            'job_queue': self.job_queue,
            'settings': self.settings
        }
        
        with open(filepath, 'w') as f:
            json.dump(state_dict, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'SessionState':
        """Load state from a JSON file."""
        if not os.path.exists(filepath):
            return cls()
        
        with open(filepath, 'r') as f:
            state_dict = json.load(f)
        
        # Convert dict back to SessionState object
        state = cls(
            continuation_mode=state_dict.get('continuation_mode', 'anchor'),
            anchor_length=state_dict.get('anchor_length', 300),
            repetition_threshold=state_dict.get('repetition_threshold', 0.8),
            backend=state_dict.get('backend', 'bridge'),
            model=state_dict.get('model', 'default'),
            window_size=state_dict.get('window_size', 100),
            current_job_id=state_dict.get('current_job_id'),
            job_queue=state_dict.get('job_queue', []),
            settings=state_dict.get('settings', {})
        )
        
        # Restore history
        for msg_dict in state_dict.get('history', []):
            timestamp = datetime.fromisoformat(msg_dict['timestamp']) if 'timestamp' in msg_dict else datetime.now()
            state.history.append(Message(
                role=msg_dict['role'],
                content=msg_dict['content'],
                timestamp=timestamp
            ))
        
        state.anchors = state_dict.get('anchors', [])
        
        return state