import { httpClient } from './client';
import type {
  Team,
  TeamCreate,
  TeamUpdate,
  TeamMember,
  TeamUser,
  Task,
  TaskShare,
  InvitationCreate,
  InvitationInfo,
} from './types';

export const teamApi = {
  async getAllTeams(): Promise<Team[]> {
    return httpClient.request<Team[]>('/teams', {
      method: 'GET',
    });
  },

  async getTeam(teamId: number): Promise<Team> {
    return httpClient.request<Team>(`/teams/${teamId}`, {
      method: 'GET',
    });
  },

  async createTeam(data: TeamCreate): Promise<Team> {
    return httpClient.request<Team>('/teams', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateTeam(teamId: number, data: TeamUpdate): Promise<Team> {
    return httpClient.request<Team>(`/teams/${teamId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteTeam(teamId: number): Promise<void> {
    return httpClient.request<void>(`/teams/${teamId}`, {
      method: 'DELETE',
    });
  },

  async regenerateInviteToken(teamId: number): Promise<Team> {
    return httpClient.request<Team>(`/teams/${teamId}/regenerate-token`, {
      method: 'POST',
    });
  },

  async getTeamMembers(teamId: number): Promise<TeamMember[]> {
    return httpClient.request<TeamMember[]>(`/teams/${teamId}/members`, {
      method: 'GET',
    });
  },

  async updateMemberRole(teamId: number, userId: number, role: 'admin' | 'member'): Promise<TeamMember> {
    return httpClient.request<TeamMember>(`/teams/${teamId}/members/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({ role }),
    });
  },

  async removeTeamMember(teamId: number, userId: number): Promise<void> {
    return httpClient.request<void>(`/teams/${teamId}/members/${userId}`, {
      method: 'DELETE',
    });
  },

  async inviteMember(teamId: number, data: InvitationCreate): Promise<any> {
    return httpClient.request<any>(`/teams/${teamId}/invitations`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getInvitation(token: string): Promise<InvitationInfo> {
    return httpClient.request<InvitationInfo>(`/invitations/${token}`, {
      method: 'GET',
      requiresAuth: false,
    });
  },

  async acceptInvitation(token: string): Promise<Team> {
    return httpClient.request<Team>(`/invitations/${token}/accept`, {
      method: 'POST',
    });
  },

  async joinTeamByToken(inviteToken: string): Promise<Team> {
    return httpClient.request<Team>(`/teams/join/${inviteToken}`, {
      method: 'POST',
    });
  },

  async getTeamUsers(teamId: number): Promise<TeamUser[]> {
    return httpClient.request<TeamUser[]>(`/teams/${teamId}/users`, {
      method: 'GET',
    });
  },

  async getTeamTasks(teamId: number): Promise<Task[]> {
    return httpClient.request<Task[]>(`/teams/${teamId}/tasks`, {
      method: 'GET',
    });
  },

  async getTaskShares(taskId: number): Promise<TaskShare[]> {
    return httpClient.request<TaskShare[]>(`/tasks/${taskId}/shares`, {
      method: 'GET',
    });
  },

  async createTaskShare(taskId: number, data: { team_id?: number; shared_with_user_id?: number; can_edit?: boolean }): Promise<TaskShare> {
    return httpClient.request<TaskShare>(`/tasks/${taskId}/shares`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteTaskShare(shareId: number): Promise<void> {
    return httpClient.request<void>(`/tasks/shares/${shareId}`, {
      method: 'DELETE',
    });
  },

  async getAssignedTasks(): Promise<Task[]> {
    return httpClient.request<Task[]>('/tasks/assigned', {
      method: 'GET',
    });
  },

  async getSharedTasks(): Promise<Task[]> {
    return httpClient.request<Task[]>('/tasks/shared', {
      method: 'GET',
    });
  },
};
