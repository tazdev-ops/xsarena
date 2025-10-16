"""Finite State Machine for the Autopilot orchestrator."""
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel
import asyncio
import logging

logger = logging.getLogger(__name__)


class State(str, Enum):
    """States for the Autopilot FSM."""
    IDLE = "idle"
    SEED = "seed"
    EXTEND = "extend"
    COMMIT = "commit"
    END = "end"
    ERROR = "error"


class FSMContext(BaseModel):
    """Context for the FSM containing state and data."""
    current_state: State = State.IDLE
    run_spec: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None
    seed_result: Optional[str] = None
    extend_result: Optional[str] = None
    commit_result: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AutopilotFSM:
    """Finite State Machine for the autopilot orchestrator."""
    
    def __init__(self):
        self.context = FSMContext()
        self.state_handlers = {
            State.IDLE: self._handle_idle,
            State.SEED: self._handle_seed,
            State.EXTEND: self._handle_extend,
            State.COMMIT: self._handle_commit,
            State.END: self._handle_end,
            State.ERROR: self._handle_error,
        }
    
    async def transition(self, new_state: State, data: Optional[Dict[str, Any]] = None):
        """Transition to a new state."""
        logger.info(f"Transitioning from {self.context.current_state} to {new_state}")
        self.context.current_state = new_state
        if data:
            # Update context with provided data
            for key, value in data.items():
                if hasattr(self.context, key):
                    setattr(self.context, key, value)
    
    async def _handle_idle(self) -> bool:
        """Handle the IDLE state."""
        logger.debug("Handling IDLE state")
        # Wait for a run spec to be provided
        return True  # Continue FSM
    
    async def _handle_seed(self) -> bool:
        """Handle the SEED state."""
        logger.debug("Handling SEED state")
        # In a real implementation, this would generate the initial seed content
        # For now, we'll just simulate it
        try:
            # Simulate seed generation
            await asyncio.sleep(0.1)  # Simulate async work
            self.context.seed_result = "Seed content generated"
            await self.transition(State.EXTEND)
            return True
        except Exception as e:
            logger.error(f"Error in SEED state: {e}")
            await self.transition(State.ERROR, {"error_message": str(e)})
            return False
    
    async def _handle_extend(self) -> bool:
        """Handle the EXTEND state."""
        logger.debug("Handling EXTEND state")
        try:
            # Simulate content extension
            await asyncio.sleep(0.1)  # Simulate async work
            self.context.extend_result = "Extended content generated"
            await self.transition(State.COMMIT)
            return True
        except Exception as e:
            logger.error(f"Error in EXTEND state: {e}")
            await self.transition(State.ERROR, {"error_message": str(e)})
            return False
    
    async def _handle_commit(self) -> bool:
        """Handle the COMMIT state."""
        logger.debug("Handling COMMIT state")
        try:
            # Simulate committing the results
            await asyncio.sleep(0.1)  # Simulate async work
            self.context.commit_result = "Results committed"
            await self.transition(State.END)
            return True
        except Exception as e:
            logger.error(f"Error in COMMIT state: {e}")
            await self.transition(State.ERROR, {"error_message": str(e)})
            return False
    
    async def _handle_end(self) -> bool:
        """Handle the END state."""
        logger.debug("Handling END state")
        return False  # Stop FSM
    
    async def _handle_error(self) -> bool:
        """Handle the ERROR state."""
        logger.error(f"Handling ERROR state: {self.context.error_message}")
        return False  # Stop FSM
    
    async def run(self, run_spec: Dict[str, Any]) -> FSMContext:
        """Run the FSM with the given run specification."""
        logger.info("Starting Autopilot FSM")
        
        # Initialize the context with the run spec
        self.context.run_spec = run_spec
        
        # Start with SEED state
        await self.transition(State.SEED)
        
        # Main loop
        continue_fsm = True
        while continue_fsm:
            current_handler = self.state_handlers.get(self.context.current_state)
            if current_handler:
                continue_fsm = await current_handler()
            else:
                logger.error(f"No handler for state: {self.context.current_state}")
                await self.transition(State.ERROR, {"error_message": f"No handler for state: {self.context.current_state}"})
                continue_fsm = False
        
        logger.info(f"FSM completed with final state: {self.context.current_state}")
        return self.context