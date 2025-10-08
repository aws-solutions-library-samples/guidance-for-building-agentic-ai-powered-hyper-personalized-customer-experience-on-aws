"""
Shared streaming utilities for agents to avoid code duplication.
"""
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class StreamingCallback:
    """Shared streaming callback class for all agents"""
    
    def __init__(self, callback_id: str, websocket_manager=None, websocket=None):
        self.callback_id = callback_id
        self.websocket_manager = websocket_manager
        self.websocket = websocket
        self.accumulated_response = ""
        
    async def on_text_chunk(self, chunk: str):
        """Handle streaming text chunks"""
        if self.websocket_manager and self.websocket:
            try:
                from models.schemas import WebSocketResponse
                stream_response = WebSocketResponse(
                    type="stream",
                    message=chunk,
                    user_id="assistant"
                )
                await self.websocket_manager.send_personal_message(
                    stream_response.model_dump_json(), 
                    self.websocket
                )
            except Exception as e:
                logger.error(f"Error sending stream chunk: {e}")


class StreamingCallbackManager:
    """Manages streaming callbacks for different agents"""
    
    def __init__(self):
        self._callbacks: Dict[str, StreamingCallback] = {}
    
    def set_callback(self, callback_id: str, websocket_manager=None, websocket=None):
        """Set streaming callback"""
        self._callbacks[callback_id] = StreamingCallback(callback_id, websocket_manager, websocket)
    
    def get_active_callback(self, agent_name: str) -> Optional[StreamingCallback]:
        """Get active callback for an agent"""
        for callback_id, callback in self._callbacks.items():
            if agent_name in callback_id:
                return callback
        return None
    
    def clear_callback(self, callback_id: str):
        """Clear specific callback"""
        if callback_id in self._callbacks:
            del self._callbacks[callback_id]
    
    def clear_agent_callbacks(self, agent_name: str):
        """Clear all callbacks for an agent"""
        to_remove = [cid for cid in self._callbacks.keys() if agent_name in cid]
        for cid in to_remove:
            del self._callbacks[cid]


# Global callback managers for each agent
bloodwork_callbacks = StreamingCallbackManager()
body_comp_callbacks = StreamingCallbackManager()
search_callbacks = StreamingCallbackManager()
