from fastapi import WebSocket
from typing import List, Dict, Optional
import os
import base64
import uuid
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_sessions: Dict[str, Dict] = {}  # user_id -> session data
        self.temp_dir = Path(tempfile.gettempdir()) / "cx_vhs_uploads"
        self.temp_dir.mkdir(exist_ok=True)

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Initialize user session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'websocket': websocket,
                'uploaded_files': [],
                'session_id': str(uuid.uuid4())
            }
        else:
            self.user_sessions[user_id]['websocket'] = websocket

    def disconnect(self, websocket: WebSocket, user_id: str = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Clean up user session and files
        if user_id and user_id in self.user_sessions:
            self._cleanup_user_files(user_id)
            del self.user_sessions[user_id]

    def _cleanup_user_files(self, user_id: str):
        """Clean up all files uploaded by a user"""
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            for file_path in session.get('uploaded_files', []):
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete file {file_path}: {e}")

    async def save_uploaded_file(self, user_id: str, file_data: str, filename: str, file_type: str) -> Optional[str]:
        """Save base64 encoded file and return file path"""
        try:
            # Decode base64 data
            file_content = base64.b64decode(file_data)
            
            # Generate unique filename
            file_extension = self._get_file_extension(file_type, filename)
            unique_filename = f"{user_id}_{uuid.uuid4()}{file_extension}"
            file_path = self.temp_dir / unique_filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Track file in user session
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['uploaded_files'].append(str(file_path))
            
            logger.info(f"Saved file: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return None

    def _get_file_extension(self, file_type: str, filename: str) -> str:
        """Get appropriate file extension based on file type and filename"""
        if filename and '.' in filename:
            return '.' + filename.split('.')[-1].lower()
        
        # Fallback based on file type
        type_extensions = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'application/pdf': '.pdf',
            'text/plain': '.txt',
            'application/json': '.json'
        }
        
        return type_extensions.get(file_type.lower(), '.bin')

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            # Check if websocket is still in active connections
            if websocket not in self.active_connections:
                logger.debug("Attempted to send message to disconnected websocket")
                return False
                
            # Check websocket state before sending
            if websocket.client_state.name != "CONNECTED":
                logger.debug(f"WebSocket not connected (state: {websocket.client_state.name})")
                return False
                
            await websocket.send_text(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            # Remove from active connections if send failed
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            return False

    async def broadcast(self, message: str):
        for connection in self.active_connections[:]:
            success = await self.send_personal_message(message, connection)
            if not success:
                # Connection was already removed by send_personal_message if it failed
                logger.debug("Removed failed connection during broadcast")

    def get_user_files(self, user_id: str) -> List[str]:
        """Get list of files uploaded by user"""
        if user_id in self.user_sessions:
            return self.user_sessions[user_id].get('uploaded_files', [])
        return []

    def set_user_agent(self, user_id: str, agent):
        """Store an agent instance for a specific user"""
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['agent'] = agent

    def get_user_agent(self, user_id: str):
        """Get the agent instance for a specific user"""
        if user_id in self.user_sessions:
            return self.user_sessions[user_id].get('agent')
        return None
