"""
Socket.io manager for real-time messaging
"""
from typing import Dict, Any, Optional
import socketio
from socketio import AsyncServer
from fastapi import FastAPI

class SocketIOManager:
    """Manages Socket.io connections and events for real-time messaging"""
    
    def __init__(self):
        self.sio: Optional[AsyncServer] = None
        self.app: Optional[FastAPI] = None
        # Store user_id to socket_id mapping
        self.user_sockets: Dict[str, str] = {}
    
    def initialize(self, app: FastAPI):
        """Initialize Socket.io with FastAPI app"""
        self.app = app
        
        # Create Socket.io server with CORS enabled
        self.sio = AsyncServer(
            cors_allowed_origins=["http://localhost:3000", "*"],
            async_mode='asgi',
            logger=True,
            engineio_logger=True
        )
        
        # Create Socket.io ASGI app that wraps the FastAPI app
        # This allows Socket.io to handle /socket.io routes and FastAPI to handle others
        self.socketio_app = socketio.ASGIApp(self.sio, other_asgi_app=app)
        
        # Register event handlers
        self._register_handlers()
        
        # Return the socketio_app so it can be used to run the server
        # Note: In main.py or where you run uvicorn, use:
        # from src.app.socketio_manager import socketio_manager
        # app = socketio_manager.socketio_app
        # Then run: uvicorn.run(app, host="0.0.0.0", port=8000)
    
    def _register_handlers(self):
        """Register Socket.io event handlers"""
        
        @self.sio.on('connect')
        async def on_connect(sid, environ, auth):
            """Handle client connection"""
            # Extract user_id from auth token or query params
            user_id = None
            if auth and 'user_id' in auth:
                user_id = auth['user_id']
            elif environ.get('QUERY_STRING'):
                # Parse query string for user_id
                query_params = dict(param.split('=') for param in environ['QUERY_STRING'].split('&') if '=' in param)
                user_id = query_params.get('user_id')
            
            if user_id:
                self.user_sockets[user_id] = sid
                await self.sio.emit('connected', {'user_id': user_id}, room=sid)
                print(f"User {user_id} connected with socket {sid}")
            else:
                print(f"Connection without user_id: {sid}")
        
        @self.sio.on('disconnect')
        async def on_disconnect(sid):
            """Handle client disconnection"""
            # Remove user from mapping
            user_id = None
            for uid, socket_id in self.user_sockets.items():
                if socket_id == sid:
                    user_id = uid
                    break
            
            if user_id:
                del self.user_sockets[user_id]
                print(f"User {user_id} disconnected")
            else:
                print(f"Unknown socket disconnected: {sid}")
        
        @self.sio.on('join_room')
        async def on_join_room(sid, data):
            """Handle joining a room (optional, for future use)"""
            room = data.get('room')
            if room:
                await self.sio.enter_room(sid, room)
                await self.sio.emit('joined_room', {'room': room}, room=sid)
    
    async def emit_new_message(self, receiver_id: str, message: Dict[str, Any]):
        """Emit new message event to a specific user"""
        if not self.sio:
            return
        
        socket_id = self.user_sockets.get(receiver_id)
        if socket_id:
            await self.sio.emit('new_message', message, room=socket_id)
            print(f"Emitted new_message to user {receiver_id}")
        else:
            print(f"User {receiver_id} not connected, message will be delivered when they reconnect")
    
    async def emit_messages_read(self, sender_id: str, receiver_id: str):
        """Emit read receipt to sender"""
        if not self.sio:
            return
        
        socket_id = self.user_sockets.get(sender_id)
        if socket_id:
            await self.sio.emit('messages_read', {
                'receiver_id': receiver_id,
                'timestamp': None  # Can add timestamp if needed
            }, room=socket_id)
            print(f"Emitted messages_read to user {sender_id}")
    
    async def emit_chat_list_update(self, user_id: str):
        """Emit chat list update event (for refreshing chat list)"""
        if not self.sio:
            return
        
        socket_id = self.user_sockets.get(user_id)
        if socket_id:
            await self.sio.emit('chat_list_update', {}, room=socket_id)
            print(f"Emitted chat_list_update to user {user_id}")

# Global instance
socketio_manager = SocketIOManager()

