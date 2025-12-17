'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { useTaskSocket } from '@/hooks/useTaskSocket';
import { useSocket } from '@/contexts/SocketContext';
import { useAuth } from '@/contexts/AuthContext';

interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  created_by: string;
  created_by_name?: string;
  assigned_to: string[];
  assigned_to_names?: string[];
  watchers: string[];
  watchers_names?: string[];
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

export default function TaskDetailPage() {
  const params = useParams();
  const taskId = params.taskId as string;
  const router = useRouter();
  const { user } = useAuth();
  const { socket, connected } = useSocket();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [newComment, setNewComment] = useState('');
  const [sendingComment, setSendingComment] = useState(false);
  const commentsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchTask = async () => {
      try {
        const data = await apiClient.get<Task>(`/tasks/${taskId}`);
        setTask(data);
        
        // Join task room for real-time updates
        if (socket && connected) {
          socket.emit('join_task', { taskId });
        }
      } catch (error) {
        console.error('Failed to fetch task:', error);
      } finally {
        setLoading(false);
      }
    };

    if (taskId) {
      fetchTask();
    }
  }, [taskId, socket, connected]);

  // Real-time updates
  useTaskSocket(
    undefined,
    (updatedTask) => {
      if (updatedTask.id === taskId) {
        setTask(updatedTask);
      }
    },
    (data) => {
      if (data.task_id === taskId) {
        setTask(data.task);
      }
    },
    (comment) => {
      if (comment.task_id === taskId) {
        setTask(prev => prev ? {
          ...prev,
          comments: [...(prev.comments || []), comment]
        } : null);
      }
    },
    (data) => {
      if (data.task_id === taskId) {
        router.push('/tasks');
      }
    }
  );

  useEffect(() => {
    commentsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [task?.comments]);

  const handleStatusChange = async (newStatus: string) => {
    if (!socket || !connected) {
      // Fallback to API
      try {
        await apiClient.put(`/tasks/${taskId}/status`, { status: newStatus });
      } catch (error) {
        console.error('Failed to update status:', error);
      }
      return;
    }

    socket.emit('task_status_changed', {
      taskId: taskId,
      status: newStatus
    });
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim() || sendingComment) return;

    setSendingComment(true);
    try {
      if (socket && connected) {
        socket.emit('task_comment', {
          taskId: taskId,
          content: newComment.trim()
        });
      } else {
        await apiClient.post(`/tasks/${taskId}/comment`, { content: newComment.trim() });
      }
      setNewComment('');
    } catch (error) {
      console.error('Failed to add comment:', error);
    } finally {
      setSendingComment(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">Task not found</p>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">Task not found</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="bg-white border-b border-gray-200 p-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{task.title}</h1>
          <div className="flex items-center space-x-2 mt-2">
            <select
              value={task.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className={`px-3 py-1 rounded-full text-sm font-medium border ${
                task.status === 'completed'
                  ? 'bg-green-100 text-green-800 border-green-300'
                  : task.status === 'in_progress'
                  ? 'bg-blue-100 text-blue-800 border-blue-300'
                  : 'bg-yellow-100 text-yellow-800 border-yellow-300'
              }`}
            >
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
            </select>
            <span className={`px-2 py-1 rounded text-xs ${
              task.priority === 'high' ? 'bg-red-100 text-red-800' :
              task.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {task.priority}
            </span>
          </div>
        </div>
        <div className="flex space-x-2">
          <Link
            href={`/tasks/${taskId}/edit`}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Edit
          </Link>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
          >
            Back
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Task Details */}
          <div className="bg-white rounded-lg shadow p-6 space-y-6">
            <div>
              <h2 className="text-sm font-medium text-gray-500 mb-1">Description</h2>
              <p className="text-gray-900 whitespace-pre-wrap">{task.description || 'No description'}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {task.assigned_to_names && task.assigned_to_names.length > 0 && (
                <div>
                  <h2 className="text-sm font-medium text-gray-500 mb-1">Assigned To</h2>
                  <p className="text-gray-900">{task.assigned_to_names.join(', ')}</p>
                </div>
              )}
              {task.watchers_names && task.watchers_names.length > 0 && (
                <div>
                  <h2 className="text-sm font-medium text-gray-500 mb-1">Watchers</h2>
                  <p className="text-gray-900">{task.watchers_names.join(', ')}</p>
                </div>
              )}
              {task.due_date && (
                <div>
                  <h2 className="text-sm font-medium text-gray-500 mb-1">Due Date</h2>
                  <p className="text-gray-900">
                    {new Date(task.due_date).toLocaleDateString()}
                  </p>
                </div>
              )}
              <div>
                <h2 className="text-sm font-medium text-gray-500 mb-1">Created</h2>
                <p className="text-gray-900">
                  {new Date(task.created_at).toLocaleDateString()} by {task.created_by_name || 'Unknown'}
                </p>
              </div>
            </div>

            {/* Attachments */}
            {task.attachments && task.attachments.length > 0 && (
              <div>
                <h2 className="text-sm font-medium text-gray-500 mb-2">Attachments</h2>
                <div className="space-y-2">
                  {task.attachments.map((attachment, idx) => (
                    <a
                      key={idx}
                      href={attachment.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-2 p-2 rounded hover:bg-gray-50"
                    >
                      <span>📎</span>
                      <span className="text-sm text-blue-600">{attachment.name}</span>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Comments Section */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Comments</h2>
            
            {/* Comments List */}
            <div className="space-y-4 mb-6">
              {task.comments && task.comments.length > 0 ? (
                task.comments.map((comment) => (
                  <div key={comment.comment_id} className="border-b border-gray-200 pb-4 last:border-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="font-semibold text-gray-900">
                            {comment.created_by_name || 'Unknown'}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(comment.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-gray-700">{comment.content}</p>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-sm">No comments yet</p>
              )}
              <div ref={commentsEndRef} />
            </div>

            {/* Add Comment Form */}
            <form onSubmit={handleAddComment} className="flex space-x-2">
              <input
                type="text"
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add a comment..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={sendingComment}
              />
              <button
                type="submit"
                disabled={!newComment.trim() || sendingComment}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sendingComment ? 'Sending...' : 'Send'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

