'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/LoadingSpinner';

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  assigned_to?: string;
  assigned_to_name?: string;
  created_at: string;
  due_date?: string;
}

export default function TaskDetailPage() {
  const params = useParams();
  const taskId = params.taskId as string;
  const router = useRouter();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTask = async () => {
      try {
        const data = await apiClient.get<Task>(`/tasks/${taskId}`);
        setTask(data);
      } catch (error) {
        console.error('Failed to fetch task:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTask();
  }, [taskId]);

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

  return (
    <div className="h-full flex flex-col">
      <div className="bg-white border-b border-gray-200 p-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{task.title}</h1>
          <span
            className={`inline-block mt-2 px-3 py-1 rounded-full text-sm font-medium ${
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
        <div className="max-w-3xl">
          <div className="bg-white rounded-lg shadow p-6 space-y-6">
            <div>
              <h2 className="text-sm font-medium text-gray-500 mb-1">Description</h2>
              <p className="text-gray-900 whitespace-pre-wrap">{task.description}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {task.assigned_to_name && (
                <div>
                  <h2 className="text-sm font-medium text-gray-500 mb-1">Assigned To</h2>
                  <p className="text-gray-900">{task.assigned_to_name}</p>
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
                  {new Date(task.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

