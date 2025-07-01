import { useEffect, useState } from 'react'
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  Avatar,
  Alert,
} from '@mui/material'
import {
  People as PeopleIcon,
  Task as TaskIcon,
  Storage as StorageIcon,
  Memory as MemoryIcon,
  TrendingUp as TrendingUpIcon,
  Key as KeyIcon,
  DeviceHub as DeviceHubIcon,
} from '@mui/icons-material'
import { api } from '../services/api'

interface UserStats {
  total: number
  active: number
  inactive: number
  new_this_week: number
  with_mfa: number
  admins: number
  regular_users: number
}

interface TaskStats {
  total: number
  by_status: Record<string, number>
  completed: number
  pending: number
  completion_rate: number
  created_in_period: number
  average_per_day: number
  overdue: number
  period_days: number
}

interface WorkspaceStats {
  total: number
  active: number
  personal: number
  shared: number
  average_members: number
  owned_by_user: number
}

interface SystemStats {
  api_keys: {
    total: number
    active: number
  }
  mcp_agents: {
    total: number
    active: number
  }
  devices: {
    total: number
    trusted: number
  }
  activity: {
    last_24_hours: number
    by_type_7_days: Record<string, number>
  }
}

export default function Dashboard() {
  const [userStats, setUserStats] = useState<UserStats | null>(null)
  const [taskStats, setTaskStats] = useState<TaskStats | null>(null)
  const [workspaceStats, setWorkspaceStats] = useState<WorkspaceStats | null>(null)
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch all statistics in parallel
      const [usersRes, tasksRes, workspacesRes, systemRes] = await Promise.all([
        api.get('/stats/users'),
        api.get('/stats/tasks'),
        api.get('/stats/workspaces'),
        api.get('/stats/system'),
      ])

      setUserStats(usersRes.data)
      setTaskStats(tasksRes.data)
      setWorkspaceStats(workspacesRes.data)
      setSystemStats(systemRes.data)
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      setError('Failed to load dashboard data. Please try again later.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <LinearProgress />
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  if (!userStats || !taskStats || !workspaceStats || !systemStats) {
    return <Typography>No data available</Typography>
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {/* User Stats */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                  <PeopleIcon />
                </Avatar>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Total Users
                  </Typography>
                  <Typography variant="h5">{userStats.total}</Typography>
                </Box>
              </Box>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box display="flex" alignItems="center">
                  <TrendingUpIcon sx={{ color: 'success.main', mr: 1, fontSize: 20 }} />
                  <Typography variant="body2" color="success.main">
                    {userStats.active} active
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {userStats.new_this_week} new
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={(userStats.active / userStats.total) * 100}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Task Stats */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Avatar sx={{ bgcolor: 'success.main', mr: 2 }}>
                  <TaskIcon />
                </Avatar>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Total Tasks
                  </Typography>
                  <Typography variant="h5">{taskStats.total}</Typography>
                </Box>
              </Box>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {taskStats.completed} completed
                </Typography>
                <Typography variant="body2" color="warning.main">
                  {taskStats.overdue} overdue
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={taskStats.completion_rate}
                sx={{ mt: 1 }}
                color="success"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Workspace Stats */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Avatar sx={{ bgcolor: 'warning.main', mr: 2 }}>
                  <StorageIcon />
                </Avatar>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Workspaces
                  </Typography>
                  <Typography variant="h5">{workspaceStats.total}</Typography>
                </Box>
              </Box>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {workspaceStats.active} active
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {workspaceStats.shared} shared
                </Typography>
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Avg {workspaceStats.average_members.toFixed(1)} members
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* System Stats */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Avatar sx={{ bgcolor: 'info.main', mr: 2 }}>
                  <MemoryIcon />
                </Avatar>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    System
                  </Typography>
                  <Typography variant="h5">
                    {systemStats.mcp_agents.active}/{systemStats.mcp_agents.total}
                  </Typography>
                </Box>
              </Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Active MCP Agents
              </Typography>
              <Box display="flex" gap={1} flexWrap="wrap">
                <Chip 
                  icon={<KeyIcon />} 
                  label={`${systemStats.api_keys.active} API Keys`} 
                  size="small" 
                />
                <Chip 
                  icon={<DeviceHubIcon />} 
                  label={`${systemStats.devices.total} Devices`} 
                  size="small" 
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Activity Overview */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Activity Overview (Last 7 Days)
            </Typography>
            <List dense>
              {Object.entries(systemStats.activity.by_type_7_days)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([action, count]) => (
                  <ListItem key={action}>
                    <ListItemText
                      primary={
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="body2">
                            {action.replace(/_/g, ' ').toLowerCase()}
                          </Typography>
                          <Typography variant="body2" fontWeight="medium">
                            {count}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
            </List>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              {systemStats.activity.last_24_hours} activities in the last 24 hours
            </Typography>
          </Paper>
        </Grid>

        {/* Task Distribution */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Task Distribution
            </Typography>
            <List dense>
              {Object.entries(taskStats.by_status).map(([status, count]) => {
                const percentage = ((count / taskStats.total) * 100).toFixed(1)
                return (
                  <ListItem key={status}>
                    <ListItemText
                      primary={
                        <Box>
                          <Box display="flex" justifyContent="space-between" mb={1}>
                            <Typography variant="body2">
                              {status.replace(/_/g, ' ')}
                            </Typography>
                            <Typography variant="body2">
                              {count} ({percentage}%)
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={parseFloat(percentage)}
                            sx={{ height: 8, borderRadius: 4 }}
                          />
                        </Box>
                      }
                    />
                  </ListItem>
                )
              })}
            </List>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Average {taskStats.average_per_day.toFixed(1)} tasks created per day
            </Typography>
          </Paper>
        </Grid>

        {/* Quick Stats */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Quick Stats
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6} sm={3}>
                <Box textAlign="center">
                  <Typography variant="h4" color="primary">
                    {userStats.with_mfa}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Users with MFA
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box textAlign="center">
                  <Typography variant="h4" color="success.main">
                    {systemStats.devices.trusted}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Trusted Devices
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box textAlign="center">
                  <Typography variant="h4" color="warning.main">
                    {workspaceStats.personal}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Personal Workspaces
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box textAlign="center">
                  <Typography variant="h4" color="info.main">
                    {taskStats.created_in_period}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Tasks This Month
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}