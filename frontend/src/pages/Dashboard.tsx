import { useState } from 'react';
import {
  Container,
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
  ListItemIcon,
  IconButton,
  Button,
  Menu,
  MenuItem,
  Divider,
} from '@mui/material';
import {
  TaskAlt as TaskIcon,
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
  Folder as FolderIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as RadioButtonUncheckedIcon,
  MoreVert as MoreVertIcon,
  Flag as FlagIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';
import { format, isToday, isTomorrow, isPast } from 'date-fns';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useSnackbar } from 'notistack';

import { useAuthStore } from '../store/authStore';
import { statsService } from '../services/statsService';
import { taskService } from '../services/taskService';
import { workspaceService } from '../services/workspaceService';
import TaskDialog from '../components/TaskDialog';
import type { Task, TaskUpdate } from '../types';

export default function Dashboard() {
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  
  const [taskMenuAnchor, setTaskMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [taskDialogOpen, setTaskDialogOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | undefined>();
  
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };
  
  // Queries
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => statsService.getUserStats(),
  });
  
  const { data: recentTasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', 'recent'],
    queryFn: () => taskService.searchTasks({ 
      limit: 5, 
      status: ['todo', 'in_progress'] 
    }),
  });
  
  const { data: workspacesData } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => workspaceService.getWorkspaces(),
  });
  const workspaces = workspacesData || [];
  const tasks = recentTasks || [];
  
  // Mutations
  const updateTaskMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TaskUpdate }) => 
      taskService.updateTask(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
  
  const deleteTaskMutation = useMutation({
    mutationFn: (id: string) => taskService.deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      enqueueSnackbar('Task deleted successfully', { variant: 'success' });
    },
  });
  
  // Handlers
  const handleTaskMenuOpen = (event: React.MouseEvent<HTMLElement>, task: Task) => {
    event.stopPropagation();
    setTaskMenuAnchor(event.currentTarget);
    setSelectedTask(task);
  };
  
  const handleTaskMenuClose = () => {
    setTaskMenuAnchor(null);
    setSelectedTask(null);
  };
  
  const handleToggleTaskStatus = async (task: Task) => {
    const newStatus = task.status === 'completed' ? 'todo' : 'completed';
    try {
      await updateTaskMutation.mutateAsync({
        id: task.id,
        data: { status: newStatus },
      });
    } catch (error: any) {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to update task', {
        variant: 'error',
      });
    }
  };
  
  const handleEditTask = () => {
    if (selectedTask) {
      setEditingTask(selectedTask);
      setTaskDialogOpen(true);
      handleTaskMenuClose();
    }
  };
  
  const handleDeleteTask = async () => {
    if (selectedTask) {
      try {
        await deleteTaskMutation.mutateAsync(selectedTask.id);
        handleTaskMenuClose();
      } catch (error: any) {
        enqueueSnackbar(error.response?.data?.detail || 'Failed to delete task', {
          variant: 'error',
        });
      }
    }
  };
  
  const formatDueDate = (date: string) => {
    const dueDate = new Date(date);
    if (isToday(dueDate)) return 'Today';
    if (isTomorrow(dueDate)) return 'Tomorrow';
    if (isPast(dueDate)) return `Overdue (${format(dueDate, 'MMM d')})`;
    return format(dueDate, 'MMM d, yyyy');
  };
  
  const getPriorityIcon = (priority: string) => {
    const color = priority === 'high' ? 'error' : priority === 'medium' ? 'warning' : 'action';
    return <FlagIcon fontSize="small" color={color} />;
  };
  
  if (statsLoading || tasksLoading) {
    return <LinearProgress />;
  }
  
  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          {getGreeting()}, {user?.name}!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here's your task overview for today
        </Typography>
      </Box>
      
      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    Total Tasks
                  </Typography>
                  <Typography variant="h4">
                    {stats?.tasks.total || 0}
                  </Typography>
                </Box>
                <TaskIcon sx={{ fontSize: 40, color: 'primary.main', opacity: 0.7 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    Completed Today
                  </Typography>
                  <Typography variant="h4">
                    {stats?.productivity.completed_today || 0}
                  </Typography>
                </Box>
                <CheckCircleIcon sx={{ fontSize: 40, color: 'success.main', opacity: 0.7 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    Pending
                  </Typography>
                  <Typography variant="h4">
                    {stats?.tasks.pending || 0}
                  </Typography>
                </Box>
                <ScheduleIcon sx={{ fontSize: 40, color: 'warning.main', opacity: 0.7 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    Workspaces
                  </Typography>
                  <Typography variant="h4">
                    {stats?.workspaces.total || 0}
                  </Typography>
                </Box>
                <FolderIcon sx={{ fontSize: 40, color: 'info.main', opacity: 0.7 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Recent Tasks */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">
                Recent Tasks
              </Typography>
              <Button
                size="small"
                endIcon={<ArrowForwardIcon />}
                onClick={() => navigate('/tasks')}
              >
                View All
              </Button>
            </Box>
            {tasks.length === 0 ? (
              <Box textAlign="center" py={4}>
                <Typography color="text.secondary">
                  No tasks yet. Create your first task!
                </Typography>
                <Button
                  variant="contained"
                  sx={{ mt: 2 }}
                  onClick={() => navigate('/tasks')}
                >
                  Create Task
                </Button>
              </Box>
            ) : (
              <List disablePadding>
                {tasks.map((task) => (
                  <ListItem
                    key={task.id}
                    secondaryAction={
                      <IconButton 
                        edge="end" 
                        aria-label="more"
                        onClick={(e) => handleTaskMenuOpen(e, task)}
                      >
                        <MoreVertIcon />
                      </IconButton>
                    }
                    sx={{ px: 0 }}
                  >
                    <ListItemIcon>
                      <IconButton
                        edge="start"
                        onClick={() => handleToggleTaskStatus(task)}
                        size="small"
                      >
                        {task.status === 'completed' ? (
                          <CheckCircleIcon color="success" />
                        ) : (
                          <RadioButtonUncheckedIcon />
                        )}
                      </IconButton>
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          {task.title}
                          {getPriorityIcon(task.priority)}
                        </Box>
                      }
                      secondary={
                        <Box display="flex" alignItems="center" gap={2} mt={0.5}>
                          {task.workspace && (
                            <Chip
                              label={`${task.workspace.emoji || '📁'} ${task.workspace.name}`}
                              size="small"
                              variant="outlined"
                            />
                          )}
                          {task.due_date && (
                            <Typography variant="caption" color={
                              isPast(new Date(task.due_date)) && task.status !== 'completed' 
                                ? 'error.main' 
                                : 'text.secondary'
                            }>
                              Due: {formatDueDate(task.due_date)}
                            </Typography>
                          )}
                        </Box>
                      }
                      primaryTypographyProps={{
                        style: {
                          textDecoration: task.status === 'completed' ? 'line-through' : 'none',
                        },
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
        
        {/* Quick Stats */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Productivity Trend
            </Typography>
            <Box sx={{ mt: 3, textAlign: 'center' }}>
              <TrendingUpIcon sx={{ fontSize: 80, color: 'success.main', opacity: 0.3 }} />
              <Typography variant="h4" color="success.main" sx={{ mt: 2 }}>
                {stats?.productivity.completed_this_week || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Completed this week
              </Typography>
            </Box>
            <Divider sx={{ my: 3 }} />
            <Typography variant="subtitle2" gutterBottom>
              Quick Stats
            </Typography>
            <Box>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2" color="text.secondary">
                  Overdue Tasks
                </Typography>
                <Typography variant="body2" fontWeight="bold" color="error.main">
                  {stats?.tasks.overdue || 0}
                </Typography>
              </Box>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2" color="text.secondary">
                  Due Today
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {stats?.tasks.due_today || 0}
                </Typography>
              </Box>
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  Due This Week
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {stats?.tasks.due_this_week || 0}
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>
      
      {/* Task Menu */}
      <Menu
        anchorEl={taskMenuAnchor}
        open={Boolean(taskMenuAnchor)}
        onClose={handleTaskMenuClose}
      >
        <MenuItem onClick={handleEditTask}>
          <EditIcon fontSize="small" sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={handleDeleteTask} sx={{ color: 'error.main' }}>
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>
      
      {/* Task Dialog */}
      <TaskDialog
        open={taskDialogOpen}
        onClose={() => {
          setTaskDialogOpen(false);
          setEditingTask(undefined);
        }}
        onSave={async (data) => {
          if (editingTask) {
            await updateTaskMutation.mutateAsync({ id: editingTask.id, data });
          }
          setTaskDialogOpen(false);
          setEditingTask(undefined);
        }}
        task={editingTask}
        workspaces={workspaces}
      />
    </Container>
  );
}