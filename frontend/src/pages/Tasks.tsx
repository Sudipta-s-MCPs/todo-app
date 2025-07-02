import { useState } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  TextField,
  InputAdornment,
  IconButton,
  Fab,
  FormControl,
  Select,
  MenuItem,
  Chip,
  CircularProgress,
  Paper,
  Button,
  Menu,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  Add as AddIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
  Clear as ClearIcon,
  Delete as DeleteIcon,
  Done as DoneIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { useDebounce } from 'use-debounce';

import TaskCard from '../components/TaskCard';
import TaskDialog from '../components/TaskDialog';
import { taskService } from '../services/taskService';
import { workspaceService } from '../services/workspaceService';
import type { Task, TaskCreate, TaskUpdate, Workspace } from '../types';

export default function Tasks() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  
  // State
  const [tab, setTab] = useState<'all' | 'active' | 'completed'>('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 300);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>('');
  const [selectedPriority, setSelectedPriority] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set());
  const [taskDialogOpen, setTaskDialogOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | undefined>();
  const [filterMenuAnchor, setFilterMenuAnchor] = useState<null | HTMLElement>(null);
  const [sortMenuAnchor, setSortMenuAnchor] = useState<null | HTMLElement>(null);

  // Queries
  const { data: workspacesData } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => workspaceService.getWorkspaces(),
  });

  const workspaces = workspacesData || [];

  const tasksQuery = useQuery({
    queryKey: ['tasks', tab, debouncedSearch, selectedWorkspace, selectedPriority, sortBy, sortOrder],
    queryFn: () => {
      const params: any = {
        query: debouncedSearch || undefined,
        limit: 50,
        offset: 0,
      };

      if (selectedWorkspace) params.workspace_id = selectedWorkspace;
      if (selectedPriority) params.priority = [selectedPriority];

      if (tab === 'active') {
        params.status = ['in_progress'];
      } else if (tab === 'completed') {
        params.status = ['completed'];
      } else if (tab === 'all') {
        params.status = ['todo', 'in_progress'];
      }

      return taskService.searchTasks(params);
    },
  });

  const tasks = tasksQuery.data || [];

  // Mutations
  const createTaskMutation = useMutation({
    mutationFn: (data: TaskCreate & { list_id?: string }) => taskService.createTask(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

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
    },
  });

  // Handlers
  const handleCreateTask = () => {
    setEditingTask(undefined);
    setTaskDialogOpen(true);
  };

  const handleEditTask = (task: Task) => {
    setEditingTask(task);
    setTaskDialogOpen(true);
  };

  const handleSaveTask = async (data: TaskCreate & { list_id?: string } | TaskUpdate) => {
    if (editingTask) {
      await updateTaskMutation.mutateAsync({ id: editingTask.id, data: data as TaskUpdate });
    } else {
      await createTaskMutation.mutateAsync(data as TaskCreate & { list_id?: string });
    }
  };

  const handleDeleteTask = async (task: Task) => {
    if (window.confirm(`Are you sure you want to delete "${task.title}"?`)) {
      try {
        await deleteTaskMutation.mutateAsync(task.id);
        enqueueSnackbar('Task deleted successfully', { variant: 'success' });
      } catch (error: any) {
        enqueueSnackbar(error.response?.data?.detail || 'Failed to delete task', {
          variant: 'error',
        });
      }
    }
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

  const handleSelectTask = (task: Task, selected: boolean) => {
    const newSelection = new Set(selectedTasks);
    if (selected) {
      newSelection.add(task.id);
    } else {
      newSelection.delete(task.id);
    }
    setSelectedTasks(newSelection);
  };

  const handleBulkDelete = async () => {
    if (selectedTasks.size === 0) return;
    
    if (window.confirm(`Delete ${selectedTasks.size} selected tasks?`)) {
      try {
        await Promise.all(
          Array.from(selectedTasks).map((id) => deleteTaskMutation.mutateAsync(id))
        );
        enqueueSnackbar(`Deleted ${selectedTasks.size} tasks`, { variant: 'success' });
        setSelectedTasks(new Set());
      } catch (error: any) {
        enqueueSnackbar('Failed to delete some tasks', { variant: 'error' });
      }
    }
  };

  const handleBulkComplete = async () => {
    if (selectedTasks.size === 0) return;
    
    try {
      await Promise.all(
        Array.from(selectedTasks).map((id) =>
          updateTaskMutation.mutateAsync({ id, data: { status: 'completed' } })
        )
      );
      enqueueSnackbar(`Completed ${selectedTasks.size} tasks`, { variant: 'success' });
      setSelectedTasks(new Set());
    } catch (error: any) {
      enqueueSnackbar('Failed to complete some tasks', { variant: 'error' });
    }
  };

  const clearFilters = () => {
    setSearch('');
    setSelectedWorkspace('');
    setSelectedPriority('');
    setSortBy('created_at');
    setSortOrder('desc');
  };

  const hasFilters = search || selectedWorkspace || selectedPriority;

  return (
    <Box>
      <Box mb={3}>
        <Typography variant="h4" gutterBottom>
          Tasks
        </Typography>
        
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <TextField
            placeholder="Search tasks..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            size="small"
            sx={{ flex: 1, maxWidth: 400 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
              endAdornment: search && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setSearch('')}>
                    <ClearIcon />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <IconButton
            onClick={(e) => setFilterMenuAnchor(e.currentTarget)}
            color={hasFilters ? 'primary' : 'default'}
          >
            <FilterIcon />
          </IconButton>

          <IconButton onClick={(e) => setSortMenuAnchor(e.currentTarget)}>
            <SortIcon />
          </IconButton>

          {selectedTasks.size > 0 && (
            <>
              <Divider orientation="vertical" flexItem />
              <Typography variant="body2" color="text.secondary">
                {selectedTasks.size} selected
              </Typography>
              <Button
                size="small"
                startIcon={<DoneIcon />}
                onClick={handleBulkComplete}
              >
                Complete
              </Button>
              <Button
                size="small"
                startIcon={<DeleteIcon />}
                onClick={handleBulkDelete}
                color="error"
              >
                Delete
              </Button>
            </>
          )}
        </Box>

        {hasFilters && (
          <Box display="flex" gap={1} alignItems="center" mb={2}>
            <Typography variant="body2" color="text.secondary">
              Filters:
            </Typography>
            {selectedWorkspace && (
              <Chip
                label={workspaces.find((w: Workspace) => w.id === selectedWorkspace)?.name}
                onDelete={() => setSelectedWorkspace('')}
                size="small"
              />
            )}
            {selectedPriority && (
              <Chip
                label={`Priority: ${selectedPriority}`}
                onDelete={() => setSelectedPriority('')}
                size="small"
              />
            )}
            <Button size="small" onClick={clearFilters}>
              Clear all
            </Button>
          </Box>
        )}

        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="All Tasks" value="all" />
          <Tab label="Active" value="active" />
          <Tab label="Completed" value="completed" />
        </Tabs>
      </Box>

      {tasksQuery.isLoading ? (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      ) : tasks.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No tasks found
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={2}>
            {hasFilters
              ? 'Try adjusting your filters'
              : 'Create your first task to get started'}
          </Typography>
          {!hasFilters && (
            <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreateTask}>
              Create Task
            </Button>
          )}
        </Paper>
      ) : (
        <Box>
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onEdit={handleEditTask}
              onDelete={handleDeleteTask}
              onToggleStatus={handleToggleTaskStatus}
              onSelect={handleSelectTask}
              selected={selectedTasks.has(task.id)}
            />
          ))}
        </Box>
      )}

      <Fab
        color="primary"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={handleCreateTask}
      >
        <AddIcon />
      </Fab>

      <TaskDialog
        open={taskDialogOpen}
        onClose={() => setTaskDialogOpen(false)}
        onSave={handleSaveTask}
        task={editingTask}
        workspaces={workspaces}
        defaultWorkspaceId={selectedWorkspace}
      />

      {/* Filter Menu */}
      <Menu
        anchorEl={filterMenuAnchor}
        open={Boolean(filterMenuAnchor)}
        onClose={() => setFilterMenuAnchor(null)}
      >
        <Box sx={{ p: 2, minWidth: 250 }}>
          <Typography variant="subtitle2" gutterBottom>
            Filter by Workspace
          </Typography>
          <FormControl fullWidth size="small" sx={{ mb: 2 }}>
            <Select
              value={selectedWorkspace}
              onChange={(e) => setSelectedWorkspace(e.target.value)}
              displayEmpty
            >
              <MenuItem value="">All Workspaces</MenuItem>
              {workspaces.map((workspace: Workspace) => (
                <MenuItem key={workspace.id} value={workspace.id}>
                  {workspace.emoji} {workspace.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Typography variant="subtitle2" gutterBottom>
            Filter by Priority
          </Typography>
          <FormControl fullWidth size="small">
            <Select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              displayEmpty
            >
              <MenuItem value="">All Priorities</MenuItem>
              <MenuItem value="low">Low</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="high">High</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Menu>

      {/* Sort Menu */}
      <Menu
        anchorEl={sortMenuAnchor}
        open={Boolean(sortMenuAnchor)}
        onClose={() => setSortMenuAnchor(null)}
      >
        <Box sx={{ p: 2, minWidth: 200 }}>
          <Typography variant="subtitle2" gutterBottom>
            Sort by
          </Typography>
          <FormControl fullWidth size="small" sx={{ mb: 2 }}>
            <Select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <MenuItem value="created_at">Created Date</MenuItem>
              <MenuItem value="updated_at">Updated Date</MenuItem>
              <MenuItem value="due_date">Due Date</MenuItem>
              <MenuItem value="priority">Priority</MenuItem>
              <MenuItem value="title">Title</MenuItem>
            </Select>
          </FormControl>

          <Typography variant="subtitle2" gutterBottom>
            Order
          </Typography>
          <FormControl fullWidth size="small">
            <Select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
            >
              <MenuItem value="asc">Ascending</MenuItem>
              <MenuItem value="desc">Descending</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Menu>
    </Box>
  );
}