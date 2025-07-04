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
  Button,
  Divider,
} from '@mui/material';
import {
  TaskAlt as TaskIcon,
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
  Folder as FolderIcon,
  CheckCircle as CheckCircleIcon,
  Flag as FlagIcon,
  ArrowForward as ArrowForwardIcon,
} from '@mui/icons-material';
import { format, isToday, isTomorrow, isPast } from 'date-fns';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '../store/authStore';
import { statsService } from '../services/statsService';
import { taskService } from '../services/taskService';

export default function Dashboard() {
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();
  
  
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
  
  const { data: focusTasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', 'focus'],
    queryFn: () => taskService.getSmartRecommendations(10),
  });
  
  const recommendations = focusTasks || [];
  
  
  
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
        
        {/* Focus Tasks */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Box>
                <Typography variant="h6">
                  Focus Tasks
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  AI-powered recommendations based on urgency and priority
                </Typography>
              </Box>
              <Button
                size="small"
                endIcon={<ArrowForwardIcon />}
                onClick={() => navigate('/tasks')}
              >
                View All
              </Button>
            </Box>
            {recommendations.length === 0 ? (
              <Box textAlign="center" py={4}>
                <Typography color="text.secondary">
                  No focus tasks available. Create tasks to see AI recommendations!
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
                {recommendations.map((recommendation) => (
                  <ListItem
                    key={recommendation.task.id}
                    sx={{ px: 0, py: 1.5 }}
                  >
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1" fontWeight="medium">
                            {recommendation.task.title}
                          </Typography>
                          {getPriorityIcon(recommendation.task.priority)}
                          <Chip
                            label={recommendation.category}
                            size="small"
                            color={
                              recommendation.urgency_score > 0.8 ? 'error' :
                              recommendation.urgency_score > 0.5 ? 'warning' : 'info'
                            }
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box mt={0.5}>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            {recommendation.recommendation_reason}
                          </Typography>
                          <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
                            {recommendation.task.workspace && (
                              <Chip
                                label={`${recommendation.task.workspace.emoji || '📁'} ${recommendation.task.workspace.name}`}
                                size="small"
                                variant="outlined"
                              />
                            )}
                            {recommendation.task.due_date && (
                              <Typography variant="caption" color={
                                isPast(new Date(recommendation.task.due_date)) && recommendation.task.status !== 'completed' 
                                  ? 'error.main' 
                                  : 'text.secondary'
                              }>
                                Due: {formatDueDate(recommendation.task.due_date)}
                              </Typography>
                            )}
                            <Typography variant="caption" color="text.secondary">
                              Urgency: {Math.round(recommendation.urgency_score * 100)}%
                            </Typography>
                          </Box>
                        </Box>
                      }
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
    </Container>
  );
}