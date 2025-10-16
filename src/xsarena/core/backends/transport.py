"""Transport interface and event models for XSArena backends."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class EventStatus(str, Enum):
    """Status of events."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseEvent(BaseModel):
    """Base class for all events."""
    event_id: str
    timestamp: float
    status: EventStatus = EventStatus.PENDING
    metadata: Optional[Dict[str, Any]] = None


class JobStarted(BaseEvent):
    """Event when a job starts."""
    job_id: str
    spec: Dict[str, Any]


class JobFailed(BaseEvent):
    """Event when a job fails."""
    job_id: str
    error_message: str
    error_type: Optional[str] = None


class ChunkStarted(BaseEvent):
    """Event when a chunk processing starts."""
    job_id: str
    chunk_id: str
    content: str


class ChunkDone(BaseEvent):
    """Event when a chunk processing completes."""
    job_id: str
    chunk_id: str
    result: str
    tokens_used: Optional[int] = None


class ChunkFailed(BaseEvent):
    """Event when a chunk processing fails."""
    job_id: str
    chunk_id: str
    error_message: str
    error_type: Optional[str] = None


class JobCompleted(BaseEvent):
    """Event when a job completes successfully."""
    job_id: str
    result_path: str
    total_chunks: int
    total_tokens: Optional[int] = None


class BackendTransport(ABC):
    """Abstract base class for backend transport implementations."""
    
    @abstractmethod
    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a payload to the backend and return the response."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is healthy and responsive."""
        pass

    @abstractmethod
    async def stream_events(self) -> List[BaseEvent]:
        """Stream events from the backend."""
        pass