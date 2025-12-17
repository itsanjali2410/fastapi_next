'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { useTaskSocket } from '@/hooks/useTaskSocket';
import { useSocket } from '@/contexts/SocketContext';

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

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_progress' | 'completed'>('all');
  const { socket, connected } = useSocket();

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const data = await apiClient.get<Task[]>('/tasks');
        setTasks(data);
      } catch (error) {
        console.error('Failed to fetch tasks:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, []);

  // Real-time task updates
  useTaskSocket(
    (task) => {
      // Task created - add to list
      setTasks(prev => [task, ...prev]);
    },
    (task) => {
      // Task updated - update in list
      setTasks(prev => prev.map(t => t.id === task.id ? task : t));
    },
    (data) => {
      // Status changed - update in list
      setTasks(prev => prev.map(t => t.id === data.task_id ? data.task : t));
    },
    undefined, // Comments handled in detail page
    (data) => {
      // Task deleted - remove from list
      setTasks(prev => prev.filter(t => t.id !== data.task_id));
    },
    (notification) => {
      // Show notification
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(notification.task_title, {
          body: notification.message,
          icon: '/favicon.ico',
        });
      }
    }
  );

  const filteredTasks = tasks.filter((task) => {
    if (filter === 'all') return true;
    return task.status === filter;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="bg-white border-b border-gray-200 p-6 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Tasks</h1>
        <Link
          href="/tasks/create"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          Create Task
        </Link>
      </div>

      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex space-x-2">
          {(['all', 'pending', 'in_progress', 'completed'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-4 py-2 rounded-lg transition ${
                filter === status
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-4">
          {filteredTasks.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>No tasks found.</p>
            </div>
          ) : (
            filteredTasks.map((task) => (
              <Link
                key={task.id}
                href={`/tasks/${task.id}`}
                className="block bg-white rounded-lg shadow p-6 hover:shadow-md transition"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900">{task.title}</h3>
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">{task.description}</p>
                    <div className="flex items-center space-x-4 mt-3 text-sm text-gray-500">
                      {task.assigned_to_names && task.assigned_to_names.length > 0 && (
                        <span>Assigned to: {task.assigned_to_names.join(', ')}</span>
                      )}
                      {task.priority && (
                        <span className={`px-2 py-1 rounded text-xs ${
                          task.priority === 'high' ? 'bg-red-100 text-red-800' :
                          task.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {task.priority}
                        </span>
                      )}
                      {task.due_date && (
                        <span>Due: {new Date(task.due_date).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-medium ${
                      task.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : task.status === 'in_progress'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {task.status.replace('_', ' ')}
                  </span>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

