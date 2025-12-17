'use client';

import { useEffect } from 'react';
import { useSocket } from '@/contexts/SocketContext';

interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  created_by: string;
  assigned_to: string[];
  watchers: string[];
  attachments: Array<{ url: string; name: string; mime: string }>;
  comments: Array<{
    comment_id: string;
    task_id: string;
    content: string;
    created_by: string;
    created_by_name?: string;
    created_at: string;
  }>;
  org_id: string;
  created_at: string;
  updated_at: string;
  due_date?: string;
}

interface TaskComment {
  comment_id: string;
  task_id: string;
  content: string;
  created_by: string;
  created_by_name?: string;
  created_at: string;
}

interface TaskNotification {
  type: string;
  task_id: string;
  task_title: string;
  message: string;
  old_status?: string;
  new_status?: string;
  comment?: string;
}

export function useTaskSocket(
  onTaskCreated?: (task: Task) => void,
  onTaskUpdated?: (task: Task) => void,
  onTaskStatusChanged?: (data: { task_id: string; status: string; old_status: string; task: Task }) => void,
  onTaskComment?: (comment: TaskComment) => void,
  onTaskDeleted?: (data: { task_id: string }) => void,
  onTaskNotification?: (notification: TaskNotification) => void
) {
  const { socket, connected } = useSocket();

  useEffect(() => {
    if (!socket || !connected) return;

    const handleTaskCreated = (task: Task) => {
      onTaskCreated?.(task);
    };

    const handleTaskUpdated = (task: Task) => {
      onTaskUpdated?.(task);
    };

    const handleTaskStatusChanged = (data: { task_id: string; status: string; old_status: string; task: Task }) => {
      onTaskStatusChanged?.(data);
    };

    const handleNewTaskComment = (comment: TaskComment) => {
      onTaskComment?.(comment);
    };

    const handleTaskDeleted = (data: { task_id: string }) => {
      onTaskDeleted?.(data);
    };

    const handleTaskNotification = (notification: TaskNotification) => {
      onTaskNotification?.(notification);
    };

    socket.on('task_created', handleTaskCreated);
    socket.on('task_updated', handleTaskUpdated);
    socket.on('task_status_changed', handleTaskStatusChanged);
    socket.on('new_task_comment', handleNewTaskComment);
    socket.on('task_deleted', handleTaskDeleted);
    socket.on('task_notification', handleTaskNotification);

    return () => {
      socket.off('task_created', handleTaskCreated);
      socket.off('task_updated', handleTaskUpdated);
      socket.off('task_status_changed', handleTaskStatusChanged);
      socket.off('new_task_comment', handleNewTaskComment);
      socket.off('task_deleted', handleTaskDeleted);
      socket.off('task_notification', handleTaskNotification);
    };
  }, [socket, connected, onTaskCreated, onTaskUpdated, onTaskStatusChanged, onTaskComment, onTaskDeleted, onTaskNotification]);
}


