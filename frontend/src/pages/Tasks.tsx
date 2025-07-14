import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  TextField,
  InputAdornment,
  IconButton,
  FormControl,
  Select,
  MenuItem,
  Chip,
  CircularProgress,
  Paper,
  Button,
  Menu,
  Divider,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
} from '@mui/material';
import {
  Search as SearchIcon,
  Add as AddIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
  Clear as ClearIcon,
  Delete as DeleteIcon,
  Done as DoneIcon,
  SmartToy as AIIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { useDebounce } from 'use-debounce';

import TaskCard from '../components/TaskCard';
import TaskDialog from '../components/TaskDialog';
import TaskDetailsDialog from '../components/TaskDetailsDialog';
import SmartTaskInput from '../components/SmartTaskInput';
import { taskService } from '../services/taskService';
import { workspaceService } from '../services/workspaceService';
import { listService } from '../services/listService';
import type { Task, TaskCreate, TaskUpdate, Workspace } from '../types';

export default function Tasks() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const { workspaceId, listId } = useParams<{ workspaceId?: string; listId?: string }>();
  
  // State
  const [tab, setTab] = useState<'all' | 'active' | 'completed' | 'archived'>('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 300);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>('');
  const [selectedPriority, setSelectedPriority] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set());
  const [taskDialogOpen, setTaskDialogOpen] = useState(false);
  const [smartTaskDialogOpen, setSmartTaskDialogOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | undefined>();
  const [viewingTask, setViewingTask] = useState<Task | undefined>();
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [filterMenuAnchor, setFilterMenuAnchor] = useState<null | HTMLElement>(null);
  const [sortMenuAnchor, setSortMenuAnchor] = useState<null | HTMLElement>(null);

  // Queries
  const { data: workspacesData } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => workspaceService.getWorkspaces(),
  });

  const workspaces = workspacesData || [];

  // Query for specific workspace and list when filtering
  const { data: currentWorkspace } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => workspaceService.getWorkspace(workspaceId!),
    enabled: !!workspaceId,
  });

  const { data: currentList } = useQuery({
    queryKey: ['list', workspaceId, listId],
    queryFn: () => listService.getList(workspaceId!, listId!),
    enabled: !!workspaceId && !!listId,
  });

  const tasksQuery = useQuery({
    queryKey: ['tasks', tab, debouncedSearch, selectedWorkspace, selectedPriority, sortBy, sortOrder, listId],
    queryFn: () => {
      // If we have a specific listId, use getListTasks instead
      if (listId) {
        const params: any = {
          limit: 50,
          offset: 0,
        };

        if (tab === 'active') {
          params.status = ['in_progress'];
        } else if (tab === 'completed') {
          params.status = ['completed'];
        } else if (tab === 'archived') {
          params.status = ['archived'];
        } else if (tab === 'all') {
          params.status = ['todo', 'in_progress'];
        }

        if (selectedPriority) params.priority = [selectedPriority];

        return taskService.getListTasks(listId, params);
      }

      // Otherwise use search
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
      } else if (tab === 'archived') {
        params.status = ['archived'];
      } else if (tab === 'all') {
        params.status = ['todo', 'in_progress'];
      }

      return taskService.searchTasks(params);
    },
  });

  const tasks = tasksQuery.data || [];

  // Defensive filter: only show tasks matching the current tab's status
  const filteredTasks = tasks.filter((task) => {
    if (tab === 'active') return task.status === 'in_progress';
    if (tab === 'completed') return task.status === 'completed';
    if (tab === 'archived') return task.status === 'archived';
    if (tab === 'all') return task.status === 'todo' || task.status === 'in_progress';
    return true;
  });

  // Mutations
  const createTaskMutation = useMutation({
    mutationFn: (data: TaskCreate & { list_id?: string }) => {
      // If we're in a specific list view, use that listId
      const taskData = listId ? { ...data, list_id: listId } : data;
      return taskService.createTask(taskData);
    },
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

  const handleViewTask = (task: Task) => {
    setViewingTask(task);
    setDetailsDialogOpen(true);
  };

  const handleEditFromDetails = () => {
    if (viewingTask) {
      setDetailsDialogOpen(false);
      setEditingTask(viewingTask);
      setTaskDialogOpen(true);
    }
  };

  const handleDeleteFromDetails = async () => {
    if (viewingTask) {
      setDetailsDialogOpen(false);
      await handleDeleteTask(viewingTask);
    }
  };

  const handleToggleFromDetails = async () => {
    if (viewingTask) {
      await handleToggleTaskStatus(viewingTask);
      // Update the viewing task with new status
      const newStatus = viewingTask.status === 'completed' ? 'todo' : 'completed';
      setViewingTask({ ...viewingTask, status: newStatus });
    }
  };

  const handleStartTask = async () => {
    if (viewingTask) {
      try {
        await updateTaskMutation.mutateAsync({
          id: viewingTask.id,
          data: { status: 'in_progress' }
        });
        enqueueSnackbar('Task started', { variant: 'success' });
        setViewingTask({ ...viewingTask, status: 'in_progress' });
      } catch (error: any) {
        enqueueSnackbar(error.response?.data?.detail || 'Failed to start task', {
          variant: 'error',
        });
      }
    }
  };

  const handlePauseTask = async () => {
    if (viewingTask) {
      try {
        await updateTaskMutation.mutateAsync({
          id: viewingTask.id,
          data: { status: 'todo' }
        });
        enqueueSnackbar('Task paused', { variant: 'success' });
        setViewingTask({ ...viewingTask, status: 'todo' });
      } catch (error: any) {
        enqueueSnackbar(error.response?.data?.detail || 'Failed to pause task', {
          variant: 'error',
        });
      }
    }
  };

  const handleArchiveTask = async () => {
    if (viewingTask) {
      try {
        await updateTaskMutation.mutateAsync({
          id: viewingTask.id,
          data: { status: 'archived' }
        });
        enqueueSnackbar('Task archived successfully', { variant: 'success' });
        setDetailsDialogOpen(false);
        setViewingTask(undefined);
      } catch (error: any) {
        enqueueSnackbar(error.response?.data?.detail || 'Failed to archive task', {
          variant: 'error',
        });
      }
    }
  };

  const handleUnarchiveTask = async () => {
    if (viewingTask) {
      try {
        await updateTaskMutation.mutateAsync({
          id: viewingTask.id,
          data: { status: 'todo' }
        });
        enqueueSnackbar('Task restored successfully', { variant: 'success' });
        setViewingTask({ ...viewingTask, status: 'todo' });
      } catch (error: any) {
        enqueueSnackbar(error.response?.data?.detail || 'Failed to restore task', {
          variant: 'error',
        });
      }
    }
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
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          {workspaceId && (
            <IconButton onClick={() => navigate(`/workspaces/${workspaceId}/lists`)}>
              <ArrowBackIcon />
            </IconButton>
          )}
          <Box flex={1}>
            <Typography variant="h4">
              {currentList 
                ? `${currentWorkspace?.emoji || '📁'} ${currentWorkspace?.name} / ${currentList.icon || '📋'} ${currentList.name}`
                : 'Tasks'
              }
            </Typography>
            {currentList && (
              <Typography variant="body2" color="text.secondary">
                Showing tasks from {currentList.name} list
              </Typography>
            )}
          </Box>
        </Box>
        
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

        {hasFilters && !listId && (
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
          <Tab label="Archived" value="archived" />
        </Tabs>
      </Box>

      {tasksQuery.isLoading ? (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      ) : filteredTasks.length === 0 ? (
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
          {filteredTasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onEdit={handleEditTask}
              onDelete={handleDeleteTask}
              onToggleStatus={handleToggleTaskStatus}
              onSelect={handleSelectTask}
              onView={handleViewTask}
              selected={selectedTasks.has(task.id)}
            />
          ))}
        </Box>
      )}

      <SpeedDial
        ariaLabel="Create task options"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        icon={<SpeedDialIcon />}
      >
        <SpeedDialAction
          icon={<AddIcon />}
          tooltipTitle="Create Task"
          onClick={handleCreateTask}
        />
        <SpeedDialAction
          icon={<AIIcon />}
          tooltipTitle="Smart Create (AI)"
          onClick={() => setSmartTaskDialogOpen(true)}
        />
      </SpeedDial>

      <TaskDialog
        open={taskDialogOpen}
        onClose={() => {
          setTaskDialogOpen(false);
          setEditingTask(undefined);
          // If we came from details view, update the viewing task
          if (viewingTask && editingTask && viewingTask.id === editingTask.id) {
            queryClient.invalidateQueries({ queryKey: ['tasks'] });
          }
        }}
        onSave={handleSaveTask}
        task={editingTask}
        workspaces={workspaces}
        defaultWorkspaceId={workspaceId || selectedWorkspace}
        defaultListId={listId}
      />

      <SmartTaskInput
        open={smartTaskDialogOpen}
        onClose={() => setSmartTaskDialogOpen(false)}
        onTaskCreated={() => {
          queryClient.invalidateQueries({ queryKey: ['tasks'] });
          queryClient.invalidateQueries({ queryKey: ['stats'] });
          enqueueSnackbar('Task created successfully!', { variant: 'success' });
        }}
        workspaces={workspaces}
        defaultWorkspaceId={workspaceId || selectedWorkspace}
        defaultListId={listId}
      />

      {/* Filter Menu */}
      <Menu
        anchorEl={filterMenuAnchor}
        open={Boolean(filterMenuAnchor)}
        onClose={() => setFilterMenuAnchor(null)}
      >
        <Box sx={{ p: 2, minWidth: 250 }}>
          {!listId && (
            <>
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
            </>
          )}

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

      {/* Task Details Dialog */}
      <TaskDetailsDialog
        open={detailsDialogOpen}
        onClose={() => {
          setDetailsDialogOpen(false);
          setViewingTask(undefined);
        }}
        task={viewingTask || null}
        onEdit={handleEditFromDetails}
        onDelete={handleDeleteFromDetails}
        onToggleStatus={handleToggleFromDetails}
        onArchive={handleArchiveTask}
        onUnarchive={handleUnarchiveTask}
        onStartTask={handleStartTask}
        onPauseTask={handlePauseTask}
      />
    </Box>
  );
}