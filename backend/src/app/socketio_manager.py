"""
Socket.io manager for real-time messaging
"""
from typing import Dict, Any, Optional, List
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
                
                # Update user status to online and notify org members
                try:
                    from src.app.db.mongo import get_database
                    from src.app.services.user_status_service import UserStatusService
                    from src.app.services.user_service import UserService
                    from src.app.services.group_chat_service import GroupChatService
                    from src.app.models.user import UserInDB
                    
                    db = get_database()
                    status_service = UserStatusService(db)
                    user_service = UserService(db)
                    group_service = GroupChatService(db)
                    
                    # Update status to online
                    await status_service.update_status(user_id, True)
                    
                    # Get user's org_id
                    user = await user_service.get_user_by_id(user_id)
                    if user and user.org_id:
                        # Join user to all their group chat rooms
                        user_groups = await group_service.get_user_groups(user_id, user.org_id)
                        for group in user_groups:
                            room_name = f"group_{group.id}"
                            await self.sio.enter_room(sid, room_name)
                            print(f"User {user_id} joined group room: {room_name}")
                        
                        # Get all org members
                        from bson import ObjectId
                        org = await db.organizations.find_one({"_id": ObjectId(user.org_id)})
                        if org:
                            member_ids = [str(mid) if isinstance(mid, ObjectId) else mid for mid in org.get("members", [])]
                            # Emit status update to all org members
                            status_obj = await status_service.get_status(user_id)
                            if status_obj:
                                for member_id in member_ids:
                                    if member_id != user_id:
                                        member_socket = self.user_sockets.get(member_id)
                                        if member_socket:
                                            await self.sio.emit('user_status_update', {
                                                'user_id': user_id,
                                                'is_online': True,
                                                'last_seen': status_obj.last_seen.isoformat() if hasattr(status_obj.last_seen, 'isoformat') else str(status_obj.last_seen),
                                                'user_name': user.name if user else None
                                            }, room=member_socket)
                except Exception as e:
                    print(f"Error updating user status on connect: {e}")
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
                
                # Update user status to offline and notify org members
                try:
                    from src.app.db.mongo import get_database
                    from src.app.services.user_status_service import UserStatusService
                    from src.app.services.user_service import UserService
                    
                    db = get_database()
                    status_service = UserStatusService(db)
                    user_service = UserService(db)
                    
                    # Update status to offline
                    await status_service.update_status(user_id, False)
                    
                    # Get user's org_id
                    user = await user_service.get_user_by_id(user_id)
                    if user and user.org_id:
                        # Get all org members
                        from bson import ObjectId
                        org = await db.organizations.find_one({"_id": ObjectId(user.org_id)})
                        if org:
                            member_ids = [str(mid) if isinstance(mid, ObjectId) else mid for mid in org.get("members", [])]
                            # Emit status update to all org members
                            status_obj = await status_service.get_status(user_id)
                            if status_obj:
                                for member_id in member_ids:
                                    if member_id != user_id:
                                        member_socket = self.user_sockets.get(member_id)
                                        if member_socket:
                                            await self.sio.emit('user_status_update', {
                                                'user_id': user_id,
                                                'is_online': False,
                                                'last_seen': status_obj.last_seen.isoformat() if hasattr(status_obj.last_seen, 'isoformat') else str(status_obj.last_seen),
                                                'user_name': user.name if user else None
                                            }, room=member_socket)
                except Exception as e:
                    print(f"Error updating user status on disconnect: {e}")
            else:
                print(f"Unknown socket disconnected: {sid}")
        
        @self.sio.on('join_room')
        async def on_join_room(sid, data):
            """Handle joining a room (optional, for future use)"""
            room = data.get('room')
            if room:
                await self.sio.enter_room(sid, room)
                await self.sio.emit('joined_room', {'room': room}, room=sid)
        
        @self.sio.on('typing')
        async def on_typing(sid, data):
            """Handle typing indicator with sender_id and receiver_id"""
            chat_id = data.get('chat_id')
            is_group = data.get('is_group', False)
            receiver_id = data.get('receiver_id')  # For 1-to-1 chats
            
            # Get user_id (sender_id) from socket
            sender_id = None
            for uid, socket_id in self.user_sockets.items():
                if socket_id == sid:
                    sender_id = uid
                    break
            
            if not sender_id or not chat_id:
                return
            
            # Emit typing to the other user(s) with sender_id and receiver_id
            if is_group:
                # For groups, emit to all members except sender
                from src.app.db.mongo import get_database
                from src.app.services.group_chat_service import GroupChatService
                db = get_database()
                group_service = GroupChatService(db)
                group = await group_service.get_group_chat(chat_id)
                if group:
                    for member_id in group.members:
                        if member_id != sender_id:
                            member_socket = self.user_sockets.get(member_id)
                            if member_socket:
                                await self.sio.emit('typing', {
                                    'sender_id': sender_id,
                                    'receiver_id': member_id,
                                    'group_chat_id': chat_id,
                                    'is_group': True
                                }, room=member_socket)
            else:
                # For 1-to-1, emit to the receiver with sender_id and receiver_id
                if receiver_id:
                    receiver_socket = self.user_sockets.get(receiver_id)
                    if receiver_socket:
                        await self.sio.emit('typing', {
                            'sender_id': sender_id,
                            'receiver_id': receiver_id,
                            'is_group': False
                        }, room=receiver_socket)
    
    async def emit_new_message(self, receiver_id_or_group_id: str, message: Dict[str, Any]):
        """Emit new message event to a specific user or group room"""
        if not self.sio:
            return
        
        # Check if this is a group message
        if message.get("group_chat_id"):
            # Emit to group room (use group_chat_id from message)
            room_name = f"group_{message['group_chat_id']}"
            await self.sio.emit('new_message', message, room=room_name)
            print(f"Emitted new_message to group room {room_name}")
        else:
            # Emit to specific user (use receiver_id_or_group_id as user_id)
            socket_id = self.user_sockets.get(receiver_id_or_group_id)
            if socket_id:
                await self.sio.emit('new_message', message, room=socket_id)
                print(f"Emitted new_message to user {receiver_id_or_group_id}")
            else:
                print(f"User {receiver_id_or_group_id} not connected, message will be delivered when they reconnect")
    
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

    async def emit_message_updated(self, user_ids: List[str], message: Dict[str, Any]):
        """Emit message update event to multiple users"""
        if not self.sio:
            return
        
        for user_id in user_ids:
            socket_id = self.user_sockets.get(user_id)
            if socket_id:
                await self.sio.emit('message_updated', message, room=socket_id)

    async def emit_message_deleted(self, user_ids: List[str], message_id: str):
        """Emit message deleted event to multiple users"""
        if not self.sio:
            return
        
        for user_id in user_ids:
            socket_id = self.user_sockets.get(user_id)
            if socket_id:
                await self.sio.emit('message_deleted', {'message_id': message_id}, room=socket_id)

    async def emit_user_status_update(self, user_id: str, status: Dict[str, Any]):
        """Emit user status update (online/offline)"""
        if not self.sio:
            return
        
        # Emit to all users in the same organization
        # This would need org_id lookup - simplified for now
        socket_id = self.user_sockets.get(user_id)
        if socket_id:
            await self.sio.emit('user_status_update', status, room=socket_id)

# Global instance
socketio_manager = SocketIOManager()

