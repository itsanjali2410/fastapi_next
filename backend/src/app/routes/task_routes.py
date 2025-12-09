"""
Task routes
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.app.schemas.task_schema import TaskCreate, TaskUpdate, TaskResponse
from src.app.dependencies import get_current_user, get_task_service
from src.app.services.task_service import TaskService
from src.app.models.user import UserInDB
from typing import List

router = APIRouter()

@router.post("/create", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
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
        "created_by": current_user.id,
        "assigned_to": task_data.assigned_to,
        "org_id": current_user.org_id,
        "status": "pending",
        "due_date": task_data.due_date
    })
    
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "created_by": task.created_by,
        "assigned_to": task.assigned_to,
        "org_id": task.org_id,
        "status": task.status,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "due_date": task.due_date
    }

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 50,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """Get all tasks in organization"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    tasks = await task_service.get_tasks_by_org(current_user.org_id, skip, limit)
    
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "created_by": t.created_by,
            "assigned_to": t.assigned_to,
            "org_id": t.org_id,
            "status": t.status,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "due_date": t.due_date
        }
        for t in tasks
    ]

@router.get("/my-tasks", response_model=List[TaskResponse])
async def get_my_tasks(
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """Get tasks assigned to current user"""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    tasks = await task_service.get_tasks_by_user(current_user.id, current_user.org_id)
    
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "created_by": t.created_by,
            "assigned_to": t.assigned_to,
            "org_id": t.org_id,
            "status": t.status,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "due_date": t.due_date
        }
        for t in tasks
    ]

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    current_user: UserInDB = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
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
    
    return {
        "id": updated.id,
        "title": updated.title,
        "description": updated.description,
        "created_by": updated.created_by,
        "assigned_to": updated.assigned_to,
        "org_id": updated.org_id,
        "status": updated.status,
        "created_at": updated.created_at,
        "updated_at": updated.updated_at,
        "due_date": updated.due_date
    }

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
    
    return {"message": "Task deleted successfully"}

