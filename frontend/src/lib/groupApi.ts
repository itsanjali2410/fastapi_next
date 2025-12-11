/**
 * Group API functions
 */
import { apiClient } from './api';

export interface Group {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  created_by: string;
  created_by_name?: string;
  members: string[];
  member_names?: string[];
  admins: string[];
  admin_names?: string[];
  avatar_url?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface GroupMessage {
  id: string;
  organization_id: string;
  sender_id: string;
  sender_name?: string;
  group_chat_id: string;
  content: string;
  created_at: string;
  is_read: boolean;
  reply_to?: string;
  edited?: boolean;
  deleted?: boolean;
  reactions?: Array<{ user_id: string; emoji: string }>;
}

export interface CreateGroupData {
  name: string;
  description?: string;
  member_ids: string[];
}

export interface GroupListResponse {
  groups: Array<{
    id: string;
    name: string;
    avatar_url?: string;
    last_message?: string;
    last_message_timestamp?: string;
    unread_count: number;
    member_count: number;
  }>;
}

export interface GroupMessagesResponse {
  messages: GroupMessage[];
  page: number;
  limit: number;
  total: number;
  has_more: boolean;
}

export const groupApi = {
  /**
   * Create a new group
   */
  async createGroup(data: CreateGroupData): Promise<Group> {
    return apiClient.post<Group>('/chat/groups', data);
  },

  /**
   * Get all groups the current user is a member of
   */
  async getUserGroups(): Promise<GroupListResponse> {
    return apiClient.get<GroupListResponse>('/chat/groups');
  },

  /**
   * Get group details
   */
  async getGroup(groupId: string): Promise<Group> {
    return apiClient.get<Group>(`/chat/groups/${groupId}`);
  },

  /**
   * Get paginated messages for a group
   */
  async getGroupMessages(groupId: string, page: number = 1): Promise<GroupMessagesResponse> {
    return apiClient.get<GroupMessagesResponse>(`/chat/groups/${groupId}/messages`, {
      params: { page, limit: 50 }
    });
  },

  /**
   * Add members to a group
   */
  async addMembers(groupId: string, userIds: string[]): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/chat/groups/${groupId}/members`, { user_ids: userIds });
  },

  /**
   * Remove a member from a group
   */
  async removeMember(groupId: string, userId: string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/chat/groups/${groupId}/members/${userId}`);
  },

  /**
   * Update group details
   */
  async updateGroup(groupId: string, data: Partial<CreateGroupData>): Promise<Group> {
    return apiClient.put<Group>(`/chat/groups/${groupId}`, data);
  },
};

