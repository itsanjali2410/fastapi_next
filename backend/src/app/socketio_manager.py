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
                        
                        # Auto-join user to all their groups
                        groups = await group_service.get_user_groups(user_id, user.org_id)
                        for group in groups:
                            room_name = f"group_{group.id}"
                            await self.sio.enter_room(sid, room_name)
                            print(f"User {user_id} auto-joined group {group.id}")
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
        
        @self.sio.on('join_group')
        async def on_join_group(sid, data):
            """Handle joining a group room"""
            group_id = data.get('groupId') or data.get('group_id')
            if not group_id:
                return
            
            # Get user_id from socket
            user_id = None
            for uid, socket_id in self.user_sockets.items():
                if socket_id == sid:
                    user_id = uid
                    break
            
            if not user_id:
                return
            
            # Verify user is a member of the group
            from src.app.db.mongo import get_database
            from src.app.services.group_chat_service import GroupChatService
            db = get_database()
            group_service = GroupChatService(db)
            group = await group_service.get_group_chat(group_id)
            
            if group and user_id in group.members:
                # Join the group room
                room_name = f"group_{group_id}"
                await self.sio.enter_room(sid, room_name)
                await self.sio.emit('joined_group', {'groupId': group_id}, room=sid)
                print(f"User {user_id} joined group {group_id}")
        
        @self.sio.on('group_message')
        async def on_group_message(sid, data):
            """Handle group message"""
            group_id = data.get('groupId') or data.get('group_id')
            sender_id = data.get('senderId') or data.get('sender_id')
            content = data.get('content')
            
            if not group_id or not sender_id or not content:
                return
            
            # Verify user is a member of the group
            from src.app.db.mongo import get_database
            from src.app.services.group_chat_service import GroupChatService
            from src.app.services.messages_service import MessagesService
            from src.app.services.user_service import UserService
            from datetime import datetime
            
            db = get_database()
            group_service = GroupChatService(db)
            messages_service = MessagesService(db)
            user_service = UserService(db)
            
            group = await group_service.get_group_chat(group_id)
            if not group or sender_id not in group.members:
                await self.sio.emit('error', {'message': 'Not a member of this group'}, room=sid)
                return
            
            # Get sender info
            sender = await user_service.get_user_by_id(sender_id)
            if not sender:
                return
            
            # Save message with read_by initialized with sender
            message_doc = {
                "organization_id": group.organization_id,
                "sender_id": sender_id,
                "group_chat_id": group_id,
                "content": content,
                "edited": False,
                "deleted": False,
                "reactions": [],
                "delivery_status": {},
                "read_by": [sender_id],  # Initialize with sender
                "read_by_details": {sender_id: datetime.utcnow()},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_read": False
            }
            
            result = await messages_service.collection.insert_one(message_doc)
            message_doc["_id"] = str(result.inserted_id)
            
            # Update conversation participants
            participants = [{"user_id": member_id, "display_name": group.name} for member_id in group.members]
            await messages_service.upsert_conversation_participants(
                conversation_id=group_id,
                convo_type="group",
                participants=participants,
                last_message_content=content,
                last_message_at=datetime.utcnow(),
                sender_id=sender_id,
                group_id=group_id
            )
            
            # Prepare message payload
            message_payload = {
                "id": message_doc["_id"],
                "organization_id": message_doc["organization_id"],
                "sender_id": message_doc["sender_id"],
                "group_chat_id": message_doc["group_chat_id"],
                "content": message_doc["content"],
                "created_at": message_doc["created_at"].isoformat(),
                "is_read": message_doc["is_read"],
                "sender_name": sender.name
            }
            
            # Emit to all group members
            room_name = f"group_{group_id}"
            await self.sio.emit('group_message', message_payload, room=room_name)
            
            # Calculate and emit unread counts for other members
            messages_collection = messages_service.collection
            for member_id in group.members:
                if member_id != sender_id:
                    # Count unread messages for this member
                    unread_count = await messages_collection.count_documents({
                        "group_chat_id": group_id,
                        "read_by": {"$ne": member_id}
                    })
                    
                    # Emit unread update to this member
                    member_socket = self.user_sockets.get(member_id)
                    if member_socket:
                        await self.sio.emit('group_unread_update', {
                            "groupId": group_id,
                            "unreadCount": unread_count
                        }, room=member_socket)
                
                # Also emit new_message for chat list updates
                await self.emit_new_message(member_id, message_payload)
                await self.emit_chat_list_update(member_id)
        
        @self.sio.on('send_message')
        async def on_send_message(sid, data):
            """Handle sending messages (personal or group) with attachments"""
            from src.app.db.mongo import get_database
            from src.app.services.group_chat_service import GroupChatService
            from src.app.services.messages_service import MessagesService
            from src.app.services.user_service import UserService
            from datetime import datetime
            from bson import ObjectId
            
            db = get_database()
            messages_service = MessagesService(db)
            user_service = UserService(db)
            
            # Get user_id from socket
            user_id = None
            for uid, socket_id in self.user_sockets.items():
                if socket_id == sid:
                    user_id = uid
                    break
            
            if not user_id:
                await self.sio.emit('error', {'message': 'User not authenticated'}, room=sid)
                return
            
            chat_type = data.get('chatType', 'personal')
            sender_id = data.get('senderId') or user_id
            receiver_id = data.get('receiverId')
            group_id = data.get('groupId')
            content = data.get('content', '')
            message_type = data.get('type', 'text')
            attachment_url = data.get('attachmentUrl')
            attachment_name = data.get('attachmentName')
            mime_type = data.get('mimeType')
            reply_to = data.get('replyTo')
            
            # Validate chat type
            if chat_type == 'personal' and not receiver_id:
                await self.sio.emit('error', {'message': 'receiverId required for personal chat'}, room=sid)
                return
            if chat_type == 'group' and not group_id:
                await self.sio.emit('error', {'message': 'groupId required for group chat'}, room=sid)
                return
            
            # Get sender info
            sender = await user_service.get_user_by_id(sender_id)
            if not sender:
                await self.sio.emit('error', {'message': 'Sender not found'}, room=sid)
                return
            
            # For group messages, verify membership
            if chat_type == 'group':
                group_service = GroupChatService(db)
                group = await group_service.get_group_chat(group_id)
                if not group or sender_id not in group.members:
                    await self.sio.emit('error', {'message': 'Not a member of this group'}, room=sid)
                    return
                organization_id = group.organization_id
            else:
                # For personal messages, verify receiver
                receiver = await user_service.get_user_by_id(receiver_id)
                if not receiver:
                    await self.sio.emit('error', {'message': 'Receiver not found'}, room=sid)
                    return
                organization_id = sender.org_id
            
            # Build message document
            message_doc = {
                "organization_id": organization_id,
                "chat_type": chat_type,
                "sender_id": sender_id,
                "receiver_id": receiver_id if chat_type == 'personal' else None,
                "group_id": group_id if chat_type == 'group' else None,
                "group_chat_id": group_id if chat_type == 'group' else None,  # Backward compatibility
                "content": content,
                "type": message_type,
                "attachment_url": attachment_url,
                "attachment_name": attachment_name,
                "mime_type": mime_type,
                "reply_to": reply_to,
                "edited": False,
                "deleted": False,
                "reactions": [],
                "delivery_status": {},
                "read_by": [sender_id] if chat_type == 'group' else [],
                "read_by_details": {sender_id: datetime.utcnow()} if chat_type == 'group' else {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_read": False
            }
            
            # Save message
            result = await messages_service.collection.insert_one(message_doc)
            message_doc["_id"] = str(result.inserted_id)
            
            # Update conversation participants
            if chat_type == 'group':
                participants = [{"user_id": member_id, "display_name": group.name} for member_id in group.members]
                await messages_service.upsert_conversation_participants(
                    conversation_id=group_id,
                    convo_type="group",
                    participants=participants,
                    last_message_content=content or f"[{message_type}]",
                    last_message_at=datetime.utcnow(),
                    sender_id=sender_id,
                    group_id=group_id
                )
            
            # Prepare message payload
            message_payload = {
                "id": message_doc["_id"],
                "chat_type": chat_type,
                "organization_id": message_doc["organization_id"],
                "sender_id": message_doc["sender_id"],
                "receiver_id": message_doc.get("receiver_id"),
                "group_id": message_doc.get("group_id"),
                "group_chat_id": message_doc.get("group_chat_id"),
                "content": message_doc["content"],
                "type": message_doc["type"],
                "attachment_url": message_doc.get("attachment_url"),
                "attachment_name": message_doc.get("attachment_name"),
                "mime_type": message_doc.get("mime_type"),
                "reply_to": message_doc.get("reply_to"),
                "created_at": message_doc["created_at"].isoformat(),
                "updated_at": message_doc["updated_at"].isoformat(),
                "sender_name": sender.name
            }
            
            # Emit message
            if chat_type == 'group':
                room_name = f"group_{group_id}"
                await self.sio.emit('receive_message', message_payload, room=room_name)
                # Also emit group_message for backward compatibility
                await self.sio.emit('group_message', message_payload, room=room_name)
                
                # Calculate and emit unread counts
                for member_id in group.members:
                    if member_id != sender_id:
                        unread_count = await messages_service.collection.count_documents({
                            "group_chat_id": group_id,
                            "read_by": {"$ne": member_id}
                        })
                        member_socket = self.user_sockets.get(member_id)
                        if member_socket:
                            await self.sio.emit('group_unread_update', {
                                "groupId": group_id,
                                "unreadCount": unread_count
                            }, room=member_socket)
            else:
                # Personal message - emit to receiver
                receiver_socket = self.user_sockets.get(receiver_id)
                if receiver_socket:
                    await self.sio.emit('receive_message', message_payload, room=receiver_socket)
                # Also emit to sender for their own message
                await self.sio.emit('receive_message', message_payload, room=sid)
                # Emit new_message for backward compatibility
                await self.emit_new_message(receiver_id, message_payload)
                await self.emit_new_message(sender_id, message_payload)
            
            # Emit chat list updates
            if chat_type == 'group':
                for member_id in group.members:
                    await self.emit_chat_list_update(member_id)
            else:
                await self.emit_chat_list_update(receiver_id)
                await self.emit_chat_list_update(sender_id)
        
        @self.sio.on('edit_message')
        async def on_edit_message(sid, data):
            """Handle editing a message"""
            from src.app.db.mongo import get_database
            from src.app.services.messages_service import MessagesService
            from datetime import datetime
            from bson import ObjectId
            
            db = get_database()
            messages_service = MessagesService(db)
            
            # Get user_id from socket
            user_id = None
            for uid, socket_id in self.user_sockets.items():
                if socket_id == sid:
                    user_id = uid
                    break
            
            if not user_id:
                await self.sio.emit('error', {'message': 'User not authenticated'}, room=sid)
                return
            
            message_id = data.get('messageId')
            new_content = data.get('newContent')
            
            if not message_id or not new_content:
                await self.sio.emit('error', {'message': 'messageId and newContent required'}, room=sid)
                return
            
            # Get message to verify ownership
            try:
                message = await messages_service.collection.find_one({"_id": ObjectId(message_id)})
                if not message:
                    await self.sio.emit('error', {'message': 'Message not found'}, room=sid)
                    return
                
                if message.get("sender_id") != user_id:
                    await self.sio.emit('error', {'message': 'Not authorized to edit this message'}, room=sid)
                    return
                
                # Update message
                await messages_service.collection.update_one(
                    {"_id": ObjectId(message_id)},
                    {
                        "$set": {
                            "content": new_content,
                            "edited": True,
                            "edited_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                
                # Prepare update payload
                update_payload = {
                    "id": message_id,
                    "content": new_content,
                    "edited": True,
                    "edited_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                # Emit to relevant users
                chat_type = message.get("chat_type", "personal")
                if chat_type == "group":
                    group_id = message.get("group_id") or message.get("group_chat_id")
                    if group_id:
                        room_name = f"group_{group_id}"
                        await self.sio.emit('message_edited', update_payload, room=room_name)
                else:
                    receiver_id = message.get("receiver_id")
                    sender_id = message.get("sender_id")
                    # Emit to both sender and receiver
                    if receiver_id:
                        receiver_socket = self.user_sockets.get(receiver_id)
                        if receiver_socket:
                            await self.sio.emit('message_edited', update_payload, room=receiver_socket)
                    if sender_id:
                        sender_socket = self.user_sockets.get(sender_id)
                        if sender_socket:
                            await self.sio.emit('message_edited', update_payload, room=sender_socket)
                
                # Also emit message_updated for backward compatibility
                await self.emit_message_updated([receiver_id, sender_id] if receiver_id else [sender_id], update_payload)
                
            except Exception as e:
                await self.sio.emit('error', {'message': f'Failed to edit message: {str(e)}'}, room=sid)
        
        @self.sio.on('group_typing')
        async def on_group_typing(sid, data):
            """Handle group typing indicator"""
            group_id = data.get('groupId') or data.get('group_id')
            user_id = data.get('userId') or data.get('user_id')
            
            if not group_id:
                # Get user_id from socket if not provided
                for uid, socket_id in self.user_sockets.items():
                    if socket_id == sid:
                        user_id = uid
                        break
            
            if not user_id or not group_id:
                return
            
            # Verify user is a member of the group
            from src.app.db.mongo import get_database
            from src.app.services.group_chat_service import GroupChatService
            db = get_database()
            group_service = GroupChatService(db)
            group = await group_service.get_group_chat(group_id)
            
            if group and user_id in group.members:
                # Emit to all group members except sender
                room_name = f"group_{group_id}"
                await self.sio.emit('group_typing', {
                    'userId': user_id,
                    'groupId': group_id
                }, room=room_name, skip_sid=sid)
        
        @self.sio.on('update_task')
        async def on_update_task(sid, data):
            """Handle task update via socket"""
            from src.app.db.mongo import get_database
            from src.app.services.task_service import TaskService
            from src.app.services.user_service import UserService
            from bson import ObjectId
            
            db = get_database()
            task_service = TaskService(db)
            user_service = UserService(db)
            
            # Get user_id from socket
            user_id = None
            for uid, socket_id in self.user_sockets.items():
                if socket_id == sid:
                    user_id = uid
                    break
            
            if not user_id:
                await self.sio.emit('error', {'message': 'User not authenticated'}, room=sid)
                return
            
            task_id = data.get('taskId') or data.get('task_id')
            if not task_id:
                await self.sio.emit('error', {'message': 'taskId required'}, room=sid)
                return
            
            # Get task
            task = await task_service.get_task_by_id(task_id)
            if not task:
                await self.sio.emit('error', {'message': 'Task not found'}, room=sid)
                return
            
            # Update task
            update_data = {k: v for k, v in data.items() if k not in ['taskId', 'task_id']}
            updated = await task_service.update_task(task_id, update_data)
            
            if updated:
                # Build response with user names (inline to avoid circular import)
                creator = await user_service.get_user_by_id(updated.created_by) if updated.created_by else None
                assigned_names = []
                for uid in (updated.assigned_to or []):
                    u = await user_service.get_user_by_id(uid)
                    if u:
                        assigned_names.append(u.name)
                watcher_names = []
                for uid in (updated.watchers or []):
                    u = await user_service.get_user_by_id(uid)
                    if u:
                        watcher_names.append(u.name)
                
                task_response = {
                    "id": updated.id,
                    "title": updated.title,
                    "description": updated.description,
                    "status": updated.status,
                    "priority": updated.priority,
                    "created_by": updated.created_by,
                    "created_by_name": creator.name if creator else None,
                    "assigned_to": updated.assigned_to or [],
                    "assigned_to_names": assigned_names,
                    "watchers": updated.watchers or [],
                    "watchers_names": watcher_names,
                    "attachments": updated.attachments or [],
                    "comments": updated.comments or [],
                    "org_id": updated.org_id,
                    "created_at": updated.created_at.isoformat() if hasattr(updated.created_at, 'isoformat') else str(updated.created_at),
                    "updated_at": updated.updated_at.isoformat() if hasattr(updated.updated_at, 'isoformat') else str(updated.updated_at),
                    "due_date": updated.due_date.isoformat() if updated.due_date and hasattr(updated.due_date, 'isoformat') else (str(updated.due_date) if updated.due_date else None)
                }
                
                # Emit to organization
                await self.sio.emit('task_updated', task_response)
        
        @self.sio.on('task_status_changed')
        async def on_task_status_changed(sid, data):
            """Handle task status change via socket"""
            from src.app.db.mongo import get_database
            from src.app.services.task_service import TaskService
            from src.app.services.user_service import UserService
            
            db = get_database()
            task_service = TaskService(db)
            user_service = UserService(db)
            
            # Get user_id from socket
            user_id = None
            for uid, socket_id in self.user_sockets.items():
                if socket_id == sid:
                    user_id = uid
                    break
            
            if not user_id:
                await self.sio.emit('error', {'message': 'User not authenticated'}, room=sid)
                return
            
            task_id = data.get('taskId') or data.get('task_id')
            new_status = data.get('status')
            
            if not task_id or not new_status:
                await self.sio.emit('error', {'message': 'taskId and status required'}, room=sid)
                return
            
            # Get task
            task = await task_service.get_task_by_id(task_id)
            if not task:
                await self.sio.emit('error', {'message': 'Task not found'}, room=sid)
                return
            
            old_status = task.status
            updated = await task_service.update_task(task_id, {"status": new_status})
            
            if updated:
                # Log activity
                await task_service.log_activity(task_id, {
                    "user_id": user_id,
                    "action": "status_changed",
                    "old_value": old_status,
                    "new_value": new_status
                })
                
                # Build response (inline to avoid circular import)
                creator = await user_service.get_user_by_id(updated.created_by) if updated.created_by else None
                assigned_names = []
                for uid in (updated.assigned_to or []):
                    u = await user_service.get_user_by_id(uid)
                    if u:
                        assigned_names.append(u.name)
                watcher_names = []
                for uid in (updated.watchers or []):
                    u = await user_service.get_user_by_id(uid)
                    if u:
                        watcher_names.append(u.name)
                
                task_response = {
                    "id": updated.id,
                    "title": updated.title,
                    "description": updated.description,
                    "status": updated.status,
                    "priority": updated.priority,
                    "created_by": updated.created_by,
                    "created_by_name": creator.name if creator else None,
                    "assigned_to": updated.assigned_to or [],
                    "assigned_to_names": assigned_names,
                    "watchers": updated.watchers or [],
                    "watchers_names": watcher_names,
                    "attachments": updated.attachments or [],
                    "comments": updated.comments or [],
                    "org_id": updated.org_id,
                    "created_at": updated.created_at.isoformat() if hasattr(updated.created_at, 'isoformat') else str(updated.created_at),
                    "updated_at": updated.updated_at.isoformat() if hasattr(updated.updated_at, 'isoformat') else str(updated.updated_at),
                    "due_date": updated.due_date.isoformat() if updated.due_date and hasattr(updated.due_date, 'isoformat') else (str(updated.due_date) if updated.due_date else None)
                }
                
                # Emit status changed event
                await self.sio.emit('task_status_changed', {
                    "task_id": task_id,
                    "status": new_status,
                    "old_status": old_status,
                    "task": task_response
                })
                
                # Notify assigned users and watchers
                all_users = set((updated.assigned_to or []) + (updated.watchers or []))
                for uid in all_users:
                    if uid != user_id:
                        user_socket = self.user_sockets.get(uid)
                        if user_socket:
                            await self.sio.emit('task_notification', {
                                "type": "status_changed",
                                "task_id": task_id,
                                "task_title": updated.title,
                                "old_status": old_status,
                                "new_status": new_status,
                                "message": f"Task '{updated.title}' status changed from {old_status} to {new_status}"
                            }, room=user_socket)
        
        @self.sio.on('task_comment')
        async def on_task_comment(sid, data):
            """Handle task comment via socket"""
            from src.app.db.mongo import get_database
            from src.app.services.task_service import TaskService
            from src.app.services.user_service import UserService
            from datetime import datetime
            
            db = get_database()
            task_service = TaskService(db)
            user_service = UserService(db)
            
            # Get user_id from socket
            user_id = None
            for uid, socket_id in self.user_sockets.items():
                if socket_id == sid:
                    user_id = uid
                    break
            
            if not user_id:
                await self.sio.emit('error', {'message': 'User not authenticated'}, room=sid)
                return
            
            task_id = data.get('taskId') or data.get('task_id')
            content = data.get('content')
            
            if not task_id or not content:
                await self.sio.emit('error', {'message': 'taskId and content required'}, room=sid)
                return
            
            # Get task
            task = await task_service.get_task_by_id(task_id)
            if not task:
                await self.sio.emit('error', {'message': 'Task not found'}, room=sid)
                return
            
            # Add comment
            comment = await task_service.add_comment(task_id, {
                "task_id": task_id,
                "content": content,
                "created_by": user_id
            })
            
            if comment:
                # Get user name
                user = await user_service.get_user_by_id(user_id)
                from src.app.schemas.task_schema import TaskCommentSchema
                comment_response = TaskCommentSchema(
                    comment_id=comment.get("comment_id"),
                    task_id=task_id,
                    content=comment["content"],
                    created_by=comment["created_by"],
                    created_by_name=user.name if user else None,
                    created_at=comment["created_at"]
                )
                
                # Emit to task room
                room_name = f"task_{task_id}"
                await self.sio.emit('new_task_comment', comment_response.model_dump(), room=room_name)
                
                # Notify assigned users and watchers
                all_users = set((task.assigned_to or []) + (task.watchers or []))
                for uid in all_users:
                    if uid != user_id:
                        user_socket = self.user_sockets.get(uid)
                        if user_socket:
                            await self.sio.emit('task_notification', {
                                "type": "comment_added",
                                "task_id": task_id,
                                "task_title": task.title,
                                "comment": content,
                                "message": f"{user.name if user else 'Someone'} commented on task '{task.title}'"
                            }, room=user_socket)
        
        @self.sio.on('join_task')
        async def on_join_task(sid, data):
            """Join a task room to receive real-time updates"""
            task_id = data.get('taskId') or data.get('task_id')
            if task_id:
                room_name = f"task_{task_id}"
                await self.sio.enter_room(sid, room_name)
                await self.sio.emit('joined_task', {'taskId': task_id}, room=sid)
        
        @self.sio.on('typing')
        async def on_typing(sid, data):
            """Handle typing indicator"""
            chat_id = data.get('chat_id')
            is_group = data.get('is_group', False)
            
            # Get user_id from socket
            user_id = None
            for uid, socket_id in self.user_sockets.items():
                if socket_id == sid:
                    user_id = uid
                    break
            
            if not user_id or not chat_id:
                return
            
            # Emit typing to the other user(s)
            if is_group:
                # For groups, emit to all members except sender
                from src.app.db.mongo import get_database
                from src.app.services.group_chat_service import GroupChatService
                db = get_database()
                group_service = GroupChatService(db)
                group = await group_service.get_group_chat(chat_id)
                if group:
                    for member_id in group.members:
                        if member_id != user_id:
                            member_socket = self.user_sockets.get(member_id)
                            if member_socket:
                                await self.sio.emit('typing', {'user_id': user_id}, room=member_socket)
            else:
                # For 1-to-1, emit to the receiver
                receiver_socket = self.user_sockets.get(chat_id)
                if receiver_socket:
                    await self.sio.emit('typing', {'user_id': user_id}, room=receiver_socket)
    
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
    
    async def emit_messages_read(self, sender_id: str, receiver_id: str, timestamp: Optional[str] = None):
        """Emit read receipt to sender with optional timestamp (ISO string)."""
        if not self.sio:
            return

        socket_id = self.user_sockets.get(sender_id)
        if socket_id:
            await self.sio.emit('messages_read', {
                'receiver_id': receiver_id,
                'timestamp': timestamp
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

