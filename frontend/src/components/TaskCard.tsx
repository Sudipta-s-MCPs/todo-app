import { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  AvatarGroup,
  Tooltip,
} from '@mui/material';
import {
  MoreVert as MoreIcon,
  Schedule as ScheduleIcon,
  Flag as FlagIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as UncheckedIcon,
  AttachFile as AttachmentIcon,
  Comment as CommentIcon,
} from '@mui/icons-material';
import { format, isToday, isTomorrow, isPast } from 'date-fns';

import type { Task } from '../types';

interface TaskCardProps {
  task: Task;
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => void;
  onToggleStatus: (task: Task) => void;
  onSelect?: (task: Task, selected: boolean) => void;
  onView?: (task: Task) => void;
  selected?: boolean;
}

export default function TaskCard({
  task,
  onEdit,
  onDelete,
  onToggleStatus,
  onSelect,
  onView,
  selected = false,
}: TaskCardProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleEdit = () => {
    handleMenuClose();
    onEdit(task);
  };

  const handleDelete = () => {
    handleMenuClose();
    onDelete(task);
  };

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleStatus(task);
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
      default:
        return 'default';
    }
  };

  const getStatusIcon = () => {
    if (task.status === 'completed') {
      return <CheckCircleIcon color="success" />;
    }
    return <UncheckedIcon />;
  };

  const formatDueDate = (date: string) => {
    const dueDate = new Date(date);
    if (isToday(dueDate)) return 'Today';
    if (isTomorrow(dueDate)) return 'Tomorrow';
    if (isPast(dueDate) && task.status !== 'completed') {
      return `Overdue (${format(dueDate, 'MMM d')})`;
    }
    return format(dueDate, 'MMM d, yyyy');
  };

  const isOverdue = task.due_date && isPast(new Date(task.due_date)) && task.status !== 'completed';

  return (
    <Card
      sx={{
        mb: 1,
        opacity: task.status === 'completed' ? 0.7 : task.status === 'archived' ? 0.5 : 1,
        border: selected ? '2px solid' : '1px solid',
        borderColor: selected ? 'primary.main' : 'divider',
        cursor: task.status === 'archived' ? 'not-allowed' : 'pointer',
        backgroundColor: task.status === 'archived' ? 'action.disabledBackground' : 'background.paper',
        filter: task.status === 'archived' ? 'grayscale(0.7)' : 'none',
        '&:hover': {
          boxShadow: task.status === 'archived' ? 1 : 2,
        },
      }}
      onClick={(e) => {
        // If clicking with Ctrl/Cmd key, select the task
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          task.status !== 'archived' && onSelect?.(task, !selected);
        } else if (onView) {
          // Otherwise, view the task details
          onView(task);
        }
      }}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box display="flex" alignItems="flex-start" gap={1}>
          <IconButton
            size="small"
            onClick={handleToggle}
            sx={{ mt: -0.5 }}
            disabled={task.status === 'archived'}
          >
            {getStatusIcon()}
          </IconButton>

          <Box flex={1}>
            <Typography
              variant="body1"
              sx={{
                textDecoration: (task.status === 'completed' || task.status === 'archived') ? 'line-through' : 'none',
                mb: 0.5,
                color: task.status === 'archived' ? 'text.disabled' : 'text.primary',
              }}
            >
              {task.title}
            </Typography>

            {task.description && (
              <Typography 
                variant="body2" 
                color={task.status === 'archived' ? 'text.disabled' : 'text.secondary'} 
                sx={{ 
                  mb: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  textDecoration: task.status === 'archived' ? 'line-through' : 'none',
                }}
              >
                {task.description}
              </Typography>
            )}

            <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
              {(task.workspace || task.list) && (
                <Chip
                  label={
                    task.workspace && task.list
                      ? `${task.workspace.emoji || '📁'} ${task.workspace.name} / ${task.list.name}`
                      : task.workspace
                      ? `${task.workspace.emoji || '📁'} ${task.workspace.name}`
                      : task.list
                      ? `📋 ${task.list.name}`
                      : ''
                  }
                  size="small"
                  variant="outlined"
                />
              )}

              <Chip
                icon={<FlagIcon />}
                label={task.priority}
                size="small"
                color={getPriorityColor(task.priority)}
                variant="outlined"
              />

              {task.due_date && (
                <Chip
                  icon={<ScheduleIcon />}
                  label={formatDueDate(task.due_date)}
                  size="small"
                  color={isOverdue ? 'error' : 'default'}
                  variant={isOverdue ? 'filled' : 'outlined'}
                />
              )}

              {task.tags && task.tags.map((tag) => (
                <Chip key={tag} label={tag} size="small" />
              ))}
              
              {/* Attachment and Comment indicators */}
              {task.attachment_count !== undefined && task.attachment_count > 0 && (
                <Chip
                  icon={<AttachmentIcon />}
                  label={task.attachment_count}
                  size="small"
                  variant="outlined"
                />
              )}
              
              {task.comment_count !== undefined && task.comment_count > 0 && (
                <Chip
                  icon={<CommentIcon />}
                  label={task.comment_count}
                  size="small"
                  variant="outlined"
                />
              )}
            </Box>

            {task.assigned_users && task.assigned_users.length > 0 && (
              <Box mt={1}>
                <AvatarGroup max={3} sx={{ justifyContent: 'flex-start' }}>
                  {task.assigned_users.map((user) => (
                    <Tooltip key={user.id} title={user.name}>
                      <Avatar
                        sx={{ width: 24, height: 24, fontSize: 12 }}
                      >
                        {user.name.charAt(0).toUpperCase()}
                      </Avatar>
                    </Tooltip>
                  ))}
                </AvatarGroup>
              </Box>
            )}
          </Box>

          <IconButton size="small" onClick={handleMenuOpen}>
            <MoreIcon />
          </IconButton>
        </Box>

        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
          anchorOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
        >
          <MenuItem onClick={handleEdit}>
            <EditIcon fontSize="small" sx={{ mr: 1 }} />
            Edit
          </MenuItem>
          <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
            <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
            Delete
          </MenuItem>
        </Menu>
      </CardContent>
    </Card>
  );
}