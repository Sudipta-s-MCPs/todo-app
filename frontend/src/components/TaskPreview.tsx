import { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  IconButton,
  Button,
  Collapse,
  Stack,
} from '@mui/material';
import {
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  CheckCircle as CompleteIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Flag as PriorityIcon,
  Schedule as DueIcon,
  Folder as WorkspaceIcon,
  List as ListIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { useSnackbar } from 'notistack';

import type { Task } from '../types';
import { taskService } from '../services/taskService';

interface TaskPreviewProps {
  task: Task;
  onUpdate?: () => void;
  onEdit?: (task: Task) => void;
}

export default function TaskPreview({ task, onUpdate, onEdit }: TaskPreviewProps) {
  const [expanded, setExpanded] = useState(false);
  const [updating, setUpdating] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  const handleComplete = async () => {
    try {
      setUpdating(true);
      await taskService.updateTask(task.id, {
        status: task.status === 'completed' ? 'todo' : 'completed',
      });
      enqueueSnackbar(
        task.status === 'completed' ? 'Task reopened' : 'Task completed',
        { variant: 'success' }
      );
      onUpdate?.();
    } catch (error) {
      enqueueSnackbar('Failed to update task', { variant: 'error' });
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this task?')) return;
    
    try {
      setUpdating(true);
      await taskService.deleteTask(task.id);
      enqueueSnackbar('Task deleted', { variant: 'success' });
      onUpdate?.();
    } catch (error) {
      enqueueSnackbar('Failed to delete task', { variant: 'error' });
    } finally {
      setUpdating(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent sx={{ pb: 1 }}>
        <Box display="flex" alignItems="flex-start" gap={1}>
          <IconButton
            size="small"
            onClick={handleComplete}
            disabled={updating}
            color={task.status === 'completed' ? 'success' : 'default'}
          >
            <CompleteIcon />
          </IconButton>

          <Box flex={1}>
            <Typography
              variant="body1"
              sx={{
                textDecoration: task.status === 'completed' ? 'line-through' : 'none',
                fontWeight: 500,
              }}
            >
              {task.title}
            </Typography>

            {task.description && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  mt: 0.5,
                  display: expanded ? 'block' : '-webkit-box',
                  WebkitLineClamp: expanded ? 'unset' : 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}
              >
                {task.description}
              </Typography>
            )}

            <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap">
              <Chip
                icon={<PriorityIcon />}
                label={task.priority}
                size="small"
                color={getPriorityColor(task.priority)}
                variant="outlined"
              />

              {task.due_date && (
                <Chip
                  icon={<DueIcon />}
                  label={format(new Date(task.due_date), 'MMM d')}
                  size="small"
                  variant="outlined"
                />
              )}

              {task.workspace && (
                <Chip
                  icon={<WorkspaceIcon />}
                  label={task.workspace.name}
                  size="small"
                  variant="outlined"
                />
              )}

              {task.tags?.map((tag) => (
                <Chip key={tag} label={tag} size="small" />
              ))}
            </Stack>

            {/* Expandable details */}
            <Collapse in={expanded}>
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Created: {format(new Date(task.created_at), 'PPp')}
                </Typography>
                {task.completed_at && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    Completed: {format(new Date(task.completed_at), 'PPp')}
                  </Typography>
                )}
                {task.creator_name && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    Created by: {task.creator_name}
                  </Typography>
                )}
              </Box>
            </Collapse>
          </Box>

          <IconButton
            size="small"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        </Box>

        {/* Action buttons */}
        <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
          <Button
            size="small"
            startIcon={<EditIcon />}
            onClick={() => onEdit?.(task)}
            disabled={updating}
          >
            Edit
          </Button>
          <Button
            size="small"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={handleDelete}
            disabled={updating}
          >
            Delete
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}