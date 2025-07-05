import { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Stack,
  Chip,
  IconButton,
  CircularProgress,
} from '@mui/material';
import {
  Check as ApproveIcon,
  Close as RejectIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Folder as WorkspaceIcon,
  Flag as PriorityIcon,
  CalendarToday as DateIcon,
  List as ListIcon,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useSnackbar } from 'notistack';
import { useQuery } from '@tanstack/react-query';

import { taskService } from '../services/taskService';
import { workspaceService } from '../services/workspaceService';
import { listService } from '../services/listService';

interface TaskSuggestion {
  title: string;
  description?: string | null;
  workspace_id: string;
  workspace_name?: string;
  list_id?: string;
  list_name?: string;
  priority: 'low' | 'medium' | 'high';
  status?: string;
  due_date?: string | null;
  tags?: string[];
  suggested?: boolean;
}

interface TaskSuggestionPreviewProps {
  suggestion: TaskSuggestion;
  onApprove?: () => void;
  onReject?: () => void;
}

export default function TaskSuggestionPreview({
  suggestion,
  onApprove,
  onReject,
}: TaskSuggestionPreviewProps) {
  const { enqueueSnackbar } = useSnackbar();
  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [editedTask, setEditedTask] = useState<TaskSuggestion>(suggestion);
  const [dueDate, setDueDate] = useState<Date | null>(
    suggestion.due_date ? new Date(suggestion.due_date) : null
  );

  // Fetch available workspaces
  const { data: workspaces = [] } = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => workspaceService.getWorkspaces(),
  });

  // Fetch lists for selected workspace
  const { data: lists = [] } = useQuery({
    queryKey: ['lists', editedTask.workspace_id],
    queryFn: () => listService.getListsByWorkspace(editedTask.workspace_id),
    enabled: !!editedTask.workspace_id,
  });

  useEffect(() => {
    setEditedTask(suggestion);
    setDueDate(suggestion.due_date ? new Date(suggestion.due_date) : null);
  }, [suggestion]);

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedTask(suggestion);
    setDueDate(suggestion.due_date ? new Date(suggestion.due_date) : null);
  };

  const handleSave = () => {
    setIsEditing(false);
  };

  const handleApprove = async () => {
    try {
      setIsCreating(true);
      // Defensive normalization for priority
      const validPriorities = ['low', 'medium', 'high'];
      let priority = editedTask.priority;
      if (!validPriorities.includes(priority)) {
        priority = 'medium';
      }
      // Create the task
      await taskService.createTask({
        title: editedTask.title,
        description: editedTask.description || undefined,
        workspace_id: editedTask.workspace_id,
        list_id: editedTask.list_id,
        priority,
        due_date: dueDate?.toISOString().split('T')[0],
        tags: editedTask.tags,
      });
      enqueueSnackbar('Task created successfully', { variant: 'success' });
      onApprove?.();
    } catch (error: any) {
      enqueueSnackbar(
        error.response?.data?.detail || 'Failed to create task',
        { variant: 'error' }
      );
    } finally {
      setIsCreating(false);
    }
  };

  const handleReject = () => {
    onReject?.();
  };

  const handleWorkspaceChange = (workspaceId: string) => {
    const workspace = workspaces.find((w) => w.id === workspaceId);
    setEditedTask({
      ...editedTask,
      workspace_id: workspaceId,
      workspace_name: workspace?.name || 'Unknown',
      list_id: undefined, // Reset list when workspace changes
      list_name: undefined,
    });
  };

  const handleListChange = (listId: string) => {
    const list = lists.find((l) => l.id === listId);
    setEditedTask({
      ...editedTask,
      list_id: listId,
      list_name: list?.name || 'Unknown',
    });
  };

  return (
    <Card sx={{ mb: 2, border: 2, borderColor: 'primary.main', borderStyle: 'dashed' }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6" color="primary">
              Task Suggestion
            </Typography>
            <Chip label="Review Required" color="warning" size="small" />
          </Box>
          
          {!isEditing && (
            <IconButton size="small" onClick={handleEdit} disabled={isCreating}>
              <EditIcon />
            </IconButton>
          )}
        </Box>

        {isEditing ? (
          <Stack spacing={2}>
            <TextField
              label="Title"
              value={editedTask.title}
              onChange={(e) => setEditedTask({ ...editedTask, title: e.target.value })}
              fullWidth
              required
            />
            
            <TextField
              label="Description"
              value={editedTask.description || ''}
              onChange={(e) => setEditedTask({ ...editedTask, description: e.target.value })}
              fullWidth
              multiline
              rows={3}
            />
            
            <FormControl fullWidth>
              <InputLabel>Workspace</InputLabel>
              <Select
                value={editedTask.workspace_id}
                label="Workspace"
                onChange={(e) => handleWorkspaceChange(e.target.value)}
                startAdornment={<WorkspaceIcon sx={{ mr: 1, color: 'action.active' }} />}
              >
                {workspaces.map((workspace) => (
                  <MenuItem key={workspace.id} value={workspace.id}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <span>{workspace.emoji || '📁'}</span>
                      <span>{workspace.name}</span>
                      {workspace.type === 'personal' && (
                        <Chip label="Personal" size="small" />
                      )}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControl fullWidth>
              <InputLabel>List</InputLabel>
              <Select
                value={editedTask.list_id || ''}
                label="List"
                onChange={(e) => handleListChange(e.target.value)}
                startAdornment={<ListIcon sx={{ mr: 1, color: 'action.active' }} />}
                disabled={!editedTask.workspace_id || lists.length === 0}
              >
                {lists.map((list) => (
                  <MenuItem key={list.id} value={list.id}>
                    {list.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={editedTask.priority}
                label="Priority"
                onChange={(e) => setEditedTask({ ...editedTask, priority: e.target.value as 'low' | 'medium' | 'high' })}
                startAdornment={<PriorityIcon sx={{ mr: 1, color: 'action.active' }} />}
              >
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
              </Select>
            </FormControl>
            
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="Due Date"
                value={dueDate}
                onChange={(newValue) => setDueDate(newValue)}
                slots={{
                  textField: (params) => (
                    <TextField
                      {...params}
                      fullWidth
                      InputProps={{
                        ...params.InputProps,
                        startAdornment: <DateIcon sx={{ mr: 1, color: 'action.active' }} />,
                      }}
                    />
                  ),
                }}
              />
            </LocalizationProvider>
            
            <Box display="flex" gap={1} justifyContent="flex-end">
              <Button startIcon={<CancelIcon />} onClick={handleCancel}>
                Cancel
              </Button>
              <Button startIcon={<SaveIcon />} variant="contained" onClick={handleSave}>
                Save Changes
              </Button>
            </Box>
          </Stack>
        ) : (
          <>
            <Stack spacing={1}>
              <Typography variant="body1" fontWeight={500}>
                {editedTask.title}
              </Typography>
              
              {editedTask.description && (
                <Typography variant="body2" color="text.secondary">
                  {editedTask.description}
                </Typography>
              )}
              
              <Box display="flex" gap={1} flexWrap="wrap">
                <Chip
                  icon={<WorkspaceIcon />}
                  label={editedTask.workspace_name || 'Unknown Workspace'}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
                {editedTask.list_name && (
                  <Chip
                    icon={<ListIcon />}
                    label={editedTask.list_name}
                    size="small"
                    color="secondary"
                    variant="outlined"
                  />
                )}
                <Chip
                  icon={<PriorityIcon />}
                  label={editedTask.priority}
                  size="small"
                  color={
                    editedTask.priority === 'high' ? 'error' :
                    editedTask.priority === 'medium' ? 'warning' : 'info'
                  }
                  variant="outlined"
                />
                {dueDate && (
                  <Chip
                    icon={<DateIcon />}
                    label={dueDate.toLocaleDateString()}
                    size="small"
                    variant="outlined"
                  />
                )}
              </Box>
            </Stack>
            
            <Box display="flex" gap={1} mt={3}>
              <Button
                variant="contained"
                color="success"
                startIcon={isCreating ? <CircularProgress size={16} /> : <ApproveIcon />}
                onClick={handleApprove}
                disabled={isCreating || !editedTask.title}
                fullWidth
              >
                Create Task
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<RejectIcon />}
                onClick={handleReject}
                disabled={isCreating}
                fullWidth
              >
                Reject
              </Button>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
}