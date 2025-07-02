import { api } from './api';

export interface TaskStats {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  overdue: number;
  due_today: number;
  due_this_week: number;
}

export interface WorkspaceStats {
  total: number;
  owned: number;
  member: number;
  tasks_count: number;
}

export interface UserStats {
  tasks: TaskStats;
  workspaces: WorkspaceStats;
  productivity: {
    completed_today: number;
    completed_this_week: number;
    completed_this_month: number;
    average_completion_time: number;
  };
}

export const statsService = {
  async getUserStats(): Promise<UserStats> {
    // Fetch stats from multiple endpoints and combine them
    const [tasksResponse, workspacesResponse] = await Promise.all([
      api.get('/stats/tasks'),
      api.get('/stats/workspaces'),
    ]);

    const tasksData = tasksResponse.data;
    const workspacesData = workspacesResponse.data;

    // Transform the backend data to match frontend expectations
    const userStats: UserStats = {
      tasks: {
        total: tasksData.total || 0,
        pending: tasksData.pending || 0,
        in_progress: tasksData.by_status?.in_progress || 0,
        completed: tasksData.completed || 0,
        overdue: tasksData.overdue || 0,
        due_today: 0, // Backend doesn't provide this, would need to calculate
        due_this_week: 0, // Backend doesn't provide this, would need to calculate
      },
      workspaces: {
        total: workspacesData.total || 0,
        owned: workspacesData.owned_by_user || 0,
        member: (workspacesData.total || 0) - (workspacesData.owned_by_user || 0),
        tasks_count: tasksData.total || 0,
      },
      productivity: {
        completed_today: 0, // Would need to be calculated from recent completions
        completed_this_week: Math.round((tasksData.created_in_period || 0) * (tasksData.completion_rate || 0) / 100),
        completed_this_month: tasksData.completed || 0,
        average_completion_time: 0, // Not provided by backend
      },
    };

    return userStats;
  },

  async getWorkspaceStats(_workspaceId: string): Promise<any> {
    // This endpoint doesn't exist in the backend yet
    // For now, return empty stats
    return {
      total_tasks: 0,
      completed_tasks: 0,
      pending_tasks: 0,
      members_count: 0,
    };
  },
};