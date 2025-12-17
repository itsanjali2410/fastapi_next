/**
 * Authentication API functions
 */

import { apiClient } from './api';

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  org_id: string | null;
  is_active: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name: string;
}

export interface InviteSignupData {
  token: string;
  email: string;
  password: string;
  name: string;
}

export const authApi = {
  /**
   * Login user - sets HttpOnly cookies
   */
  async login(credentials: LoginCredentials): Promise<{ message: string }> {
    return apiClient.post('/auth/login', credentials);
  },

  /**
   * Register new admin user - sets HttpOnly cookies
   */
  async register(data: RegisterData): Promise<{ message: string }> {
    return apiClient.post('/auth/register', data);
  },

  /**
   * Get current user info
   */
  async getCurrentUser(): Promise<User> {
    return apiClient.get('/auth/me');
  },

  /**
   * Logout user - clears cookies
   */
  async logout(): Promise<void> {
    return apiClient.post('/auth/logout');
  },

  /**
   * Refresh access token - uses refresh token from HttpOnly cookie
   */
  async refreshToken(): Promise<void> {
    return apiClient.post('/auth/refresh');
  },

  /**
   * Use invite link to signup
   */
  async useInviteLink(data: InviteSignupData): Promise<{ message: string }> {
    return apiClient.post('/invites/use', {
      token: data.token,
      email: data.email,
      password: data.password,
      name: data.name,
    });
  },
};


