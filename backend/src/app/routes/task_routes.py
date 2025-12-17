"""
Task routes with real-time Socket.io integration
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.app.schemas.task_schema import (
    TaskCreate, TaskUpdate, TaskResponse, TaskStatusUpdate,
    TaskCommentCreate, TaskCommentSchema, TaskAssignRequest, TaskWatchRequest
)
from src.app.dependencies import get_current_user, get_task_service, get_user_service
from src.app.services.task_service import TaskService
from src.app.services.user_service import UserService
from src.app.models.user import UserInDB
from src.app.socketio_manager import socketio_manager
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

router = APIRouter()

async def build_task_response(task, user_service: UserService):
    """Helper to build task response with user names"""
    # Get creator name
    creator = await user_service.get_user_by_id(task.created_by) if task.created_by else None
    
    # Get assigned user names
    assigned_names = []
    for user_id in (task.assigned_to or []):
        user = await user_service.get_user_by_id(user_id)
        if user:
            assigned_names.append(user.name)
    
    # Get watcher names
    watcher_names = []
    for user_id in (task.watchers or []):
        user = await user_service.get_user_by_id(user_id)
        if user:
            watcher_names.append(user.name)
    
    # Get comment creator names
    comments_with_names = []
    if task.comments:
        for comment in task.comments:
            comment_dict = comment if isinstance(comment, dict) else comment.__dict__ if hasattr(comment, '__dict__') else {}
            comment_user_id = comment_dict.get('created_by') or (comment.created_by if hasattr(comment, 'created_by') else None)
            comment_user = await user_service.get_user_by_id(comment_user_id) if comment_user_id else None
            comments_with_names.append(TaskCommentSchema(
                comment_id=comment_dict.get('comment_id') or comment_dict.get('_id'),
                task_id=task.id,
                content=comment_dict.get('content', ''),
                created_by=comment_user_id or '',
                created_by_name=comment_user.name if comment_user else None,
                created_at=comment_dict.get('created_at', datetime.utcnow())
            ))
    
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        created_by=task.created_by,
        created_by_name=creator.name if creator else None,
        assigned_to=task.assigned_to or [],
        assigned_to_names=assigned_names,
        watchers=task.watchers or [],
        watchers_names=watcher_names,
        attachments=task.attachments or [],
        comments=comments_with_names,
        org_id=task.org_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        due_date=task.due_date
    )

@router.post("", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """Create a new task"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    task = await task_service.create_task({
        "title": task_data.title,
        "description": task_data.description,
        "status": task_data.status or "pending",
        "priority": task_data.priority or "medium",
        "created_by": current_user.id,
        "assigned_to": task_data.assigned_to or [],
        "watchers": task_data.watchers or [],
        "org_id": current_user.org_id,
        "attachments": [],
        "comments": [],
        "due_date": task_data.due_date
    })
    
    response = await build_task_response(task, user_service)
    
    # Emit task_created event to organization
    if socketio_manager.sio:
        # Use JSON mode to serialize datetime/ObjectId for Socket.IO payloads
        task_payload = response.model_dump(mode="json")
        org_room = f"org_{current_user.org_id}"
        await socketio_manager.sio.emit('task_created', task_payload, room=org_room)
        # Also notify assigned users
        for user_id in task.assigned_to:
            user_socket = socketio_manager.user_sockets.get(user_id)
            if user_socket:
                await socketio_manager.sio.emit('task_notification', {
                    "type": "task_assigned",
                    "task_id": task.id,
                    "task_title": task.title,
                    "message": f"You have been assigned to task: {task.title}"
                }, room=user_socket)
    
    return response

@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    assigned_to: Optional[str] = Query(default=None),
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """Get all tasks in organization with optional filters"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    tasks = await task_service.get_tasks_by_org(
        current_user.org_id, 
        skip, 
        limit, 
        status=status,
        assigned_to=assigned_to
    )
    
    responses = []
    for task in tasks:
        responses.append(await build_task_response(task, user_service))
    
    return responses

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """Get task details"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    task = await task_service.get_task_by_id(task_id)
    if not task or task.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return await build_task_response(task, user_service)

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """Update task"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    task = await task_service.get_task_by_id(task_id)
    if not task or task.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    update_dict = task_data.model_dump(exclude_unset=True)
    updated = await task_service.update_task(task_id, update_dict)
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    response = await build_task_response(updated, user_service)
    
    # Emit task_updated event
    if socketio_manager.sio:
        task_payload = response.model_dump(mode="json")
        org_room = f"org_{current_user.org_id}"
        await socketio_manager.sio.emit('task_updated', task_payload, room=org_room)
    
    return response

@router.put("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: str,
    status_data: TaskStatusUpdate,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """Update task status only"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    task = await task_service.get_task_by_id(task_id)
    if not task or task.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    old_status = task.status
    updated = await task_service.update_task(task_id, {"status": status_data.status})
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Log activity
    await task_service.log_activity(task_id, {
        "user_id": current_user.id,
        "action": "status_changed",
        "old_value": old_status,
        "new_value": status_data.status
    })
    
    response = await build_task_response(updated, user_service)
    
    # Emit task_status_changed event
    if socketio_manager.sio:
        org_room = f"org_{current_user.org_id}"
        await socketio_manager.sio.emit('task_status_changed', {
            "task_id": task_id,
            "status": status_data.status,
            "old_status": old_status,
            "task": response.model_dump(mode="json")
        }, room=org_room)
        
        # Notify assigned users and watchers
        all_users = set((updated.assigned_to or []) + (updated.watchers or []))
        for user_id in all_users:
            if user_id != current_user.id:
                user_socket = socketio_manager.user_sockets.get(user_id)
                if user_socket:
                    await socketio_manager.sio.emit('task_notification', {
                        "type": "status_changed",
                        "task_id": task_id,
                        "task_title": updated.title,
                        "old_status": old_status,
                        "new_status": status_data.status,
                        "message": f"Task '{updated.title}' status changed from {old_status} to {status_data.status}"
                    }, room=user_socket)
    
    return response

@router.post("/{task_id}/comment", response_model=TaskCommentSchema)
async def add_comment(
    task_id: str,
    comment_data: TaskCommentCreate,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """Add a comment to a task"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    task = await task_service.get_task_by_id(task_id)
    if not task or task.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    comment = await task_service.add_comment(task_id, {
        "task_id": task_id,
        "content": comment_data.content,
        "created_by": current_user.id
    })
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add comment"
        )
    
    # Get user name
    user = await user_service.get_user_by_id(current_user.id)
    comment_response = TaskCommentSchema(
        comment_id=comment.get("comment_id"),
        task_id=task_id,
        content=comment["content"],
        created_by=comment["created_by"],
        created_by_name=user.name if user else None,
        created_at=comment["created_at"]
    )
    
    # Emit new_task_comment event
    if socketio_manager.sio:
        room_name = f"task_{task_id}"
        await socketio_manager.sio.emit('new_task_comment', comment_response.model_dump(mode="json"), room=room_name)
        
        # Notify assigned users and watchers
        all_users = set((task.assigned_to or []) + (task.watchers or []))
        for user_id in all_users:
            if user_id != current_user.id:
                user_socket = socketio_manager.user_sockets.get(user_id)
                if user_socket:
                    await socketio_manager.sio.emit('task_notification', {
                        "type": "comment_added",
                        "task_id": task_id,
                        "task_title": task.title,
                        "comment": comment_data.content,
                        "message": f"{user.name if user else 'Someone'} commented on task '{task.title}'"
                    }, room=user_socket)
    
    return comment_response

@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_users(
    task_id: str,
    assign_data: TaskAssignRequest,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """Assign users to a task"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    task = await task_service.get_task_by_id(task_id)
    if not task or task.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    updated = await task_service.update_task(task_id, {"assigned_to": assign_data.user_ids})
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    response = await build_task_response(updated, user_service)
    
    # Emit task_updated event
    if socketio_manager.sio:
        org_room = f"org_{current_user.org_id}"
        await socketio_manager.sio.emit('task_updated', response.model_dump(mode="json"), room=org_room)
        
        # Notify newly assigned users
        for user_id in assign_data.user_ids:
            if user_id not in (task.assigned_to or []):
                user_socket = socketio_manager.user_sockets.get(user_id)
                if user_socket:
                    await socketio_manager.sio.emit('task_notification', {
                        "type": "task_assigned",
                        "task_id": task_id,
                        "task_title": task.title,
                        "message": f"You have been assigned to task: {task.title}"
                    }, room=user_socket)
    
    return response

@router.post("/{task_id}/watch", response_model=dict)
async def watch_task(
    task_id: str,
    watch_data: TaskWatchRequest,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """Start or stop watching a task"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    task = await task_service.get_task_by_id(task_id)
    if not task or task.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    watchers = task.watchers or []
    if watch_data.watch:
        if current_user.id not in watchers:
            watchers.append(current_user.id)
    else:
        watchers = [w for w in watchers if w != current_user.id]
    
    await task_service.update_task(task_id, {"watchers": watchers})
    
    return {"message": "Watching task" if watch_data.watch else "Stopped watching task"}

@router.post("/{task_id}/attachment", response_model=dict)
async def add_task_attachment(
    task_id: str,
    attachment_data: dict,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """Add an attachment to a task"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    task = await task_service.get_task_by_id(task_id)
    if not task or task.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    attachment = {
        "url": attachment_data.get("url"),
        "name": attachment_data.get("name"),
        "mime": attachment_data.get("mime")
    }
    
    success = await task_service.add_attachment(task_id, attachment)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add attachment"
        )
    
    # Emit task_attachment_added event
    if socketio_manager.sio:
        room_name = f"task_{task_id}"
        await socketio_manager.sio.emit('task_attachment_added', {
            "task_id": task_id,
            "attachment": attachment
        }, room=room_name)
    
    return {"message": "Attachment added successfully", "attachment": attachment}

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """Delete task"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    task = await task_service.get_task_by_id(task_id)
    if not task or task.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    success = await task_service.delete_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Emit task_deleted event
    if socketio_manager.sio:
        org_room = f"org_{current_user.org_id}"
        await socketio_manager.sio.emit('task_deleted', {"task_id": task_id}, room=org_room)
    
    return {"message": "Task deleted successfully"}
