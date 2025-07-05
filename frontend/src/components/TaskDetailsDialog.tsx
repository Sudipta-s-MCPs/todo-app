import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  IconButton,
  Stack,
  Divider,
  Tabs,
  Tab,
  Tooltip,
  Avatar,
  AvatarGroup,
  Grid,
} from '@mui/material';
import {
  Close as CloseIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon,
  Unarchive as UnarchiveIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as UncheckedIcon,
  Schedule as ScheduleIcon,
  Flag as FlagIcon,
  Person as PersonIcon,
  CalendarToday as CalendarIcon,
  Update as UpdateIcon,
  AttachFile as AttachmentIcon,
  Comment as CommentIcon,
  Info as InfoIcon,
  Assignment as TaskIcon,
} from '@mui/icons-material';
import { format, formatDistanceToNow, isToday, isTomorrow, isPast } from 'date-fns';

import type { Task } from '../types';
import TaskAttachments from './TaskAttachments';

interface TaskDetailsDialogProps {
  open: boolean;
  onClose: () => void;
  task: Task | null;
  onEdit: () => void;
  onDelete: () => void;
  onToggleStatus: () => void;
  onArchive?: () => void;
  onUnarchive?: () => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`task-tabpanel-${index}`}
      aria-labelledby={`task-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

export default function TaskDetailsDialog({
  open,
  onClose,
  task,
  onEdit,
  onDelete,
  onToggleStatus,
  onArchive,
  onUnarchive,
}: TaskDetailsDialogProps) {
  const [tabValue, setTabValue] = useState(0);

  if (!task) return null;

  const handleClose = () => {
    setTabValue(0);
    onClose();
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  const getStatusIcon = () => {
    switch (task.status) {
      case 'completed':
        return <CheckCircleIcon color="success" />;
      case 'in_progress':
        return <UpdateIcon color="primary" />;
      case 'archived':
        return <ArchiveIcon color="disabled" />;
      default:
        return <UncheckedIcon />;
    }
  };

  const formatDueDate = (date: string) => {
    const dueDate = new Date(date);
    if (isToday(dueDate)) return 'Today';
    if (isTomorrow(dueDate)) return 'Tomorrow';
    return format(dueDate, 'MMM d, yyyy');
  };

  const isOverdue = task.due_date && isPast(new Date(task.due_date)) && task.status !== 'completed';
  const canModify = task.status !== 'archived';

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          minHeight: '60vh',
        },
      }}
    >
      <DialogTitle sx={{ m: 0, p: 2, pr: 6 }}>
        <Box display="flex" alignItems="center" gap={1}>
          {getStatusIcon()}
          <Typography variant="h6" component="span">
            {task.title}
          </Typography>
        </Box>
        <IconButton
          aria-label="close"
          onClick={handleClose}
          sx={{
            position: 'absolute',
            right: 8,
            top: 8,
            color: (theme) => theme.palette.grey[500],
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <Divider />

      <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
        <Tabs value={tabValue} onChange={(_, value) => setTabValue(value)}>
          <Tab icon={<InfoIcon />} label="Details" iconPosition="start" />
          <Tab
            icon={<AttachmentIcon />}
            label={`Attachments ${task.attachment_count ? `(${task.attachment_count})` : ''}`}
            iconPosition="start"
          />
          <Tab
            icon={<CommentIcon />}
            label={`Activity ${task.comment_count ? `(${task.comment_count})` : ''}`}
            iconPosition="start"
            disabled
          />
        </Tabs>
      </Box>

      <DialogContent>
        <TabPanel value={tabValue} index={0}>
          {/* Details Tab */}
          <Stack spacing={3}>
            {/* Description */}
            {task.description && (
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Description
                </Typography>
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                  {task.description}
                </Typography>
              </Box>
            )}

            {/* Properties Grid */}
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <Stack spacing={2}>
                  {/* Status */}
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Status
                    </Typography>
                    <Chip
                      icon={getStatusIcon()}
                      label={task.status.replace('_', ' ')}
                      color={task.status === 'completed' ? 'success' : 'default'}
                      variant={task.status === 'archived' ? 'outlined' : 'filled'}
                    />
                  </Box>

                  {/* Priority */}
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Priority
                    </Typography>
                    <Chip
                      icon={<FlagIcon />}
                      label={task.priority}
                      color={getPriorityColor(task.priority)}
                      size="small"
                    />
                  </Box>

                  {/* Due Date */}
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Due Date
                    </Typography>
                    {task.due_date ? (
                      <Chip
                        icon={<ScheduleIcon />}
                        label={formatDueDate(task.due_date)}
                        color={isOverdue ? 'error' : 'default'}
                        variant={isOverdue ? 'filled' : 'outlined'}
                        size="small"
                      />
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No due date
                      </Typography>
                    )}
                  </Box>

                  {/* Workspace & List */}
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Location
                    </Typography>
                    <Stack direction="row" spacing={1}>
                      {task.workspace && (
                        <Chip
                          label={`${task.workspace.emoji || '📁'} ${task.workspace.name}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                      {task.list && (
                        <Chip
                          icon={<TaskIcon />}
                          label={task.list.name}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Box>
                </Stack>
              </Grid>

              <Grid item xs={12} sm={6}>
                <Stack spacing={2}>
                  {/* Created By */}
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Created By
                    </Typography>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Avatar sx={{ width: 24, height: 24 }}>
                        <PersonIcon fontSize="small" />
                      </Avatar>
                      <Typography variant="body2">
                        {task.creator_name || 'Unknown'}
                      </Typography>
                    </Stack>
                  </Box>

                  {/* Assigned To */}
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Assigned To
                    </Typography>
                    {task.assigned_users && task.assigned_users.length > 0 ? (
                      <AvatarGroup max={4} sx={{ justifyContent: 'flex-start' }}>
                        {task.assigned_users.map((user) => (
                          <Tooltip key={user.id} title={user.name}>
                            <Avatar sx={{ width: 32, height: 32 }}>
                              {user.name.charAt(0).toUpperCase()}
                            </Avatar>
                          </Tooltip>
                        ))}
                      </AvatarGroup>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        Unassigned
                      </Typography>
                    )}
                  </Box>

                  {/* Created At */}
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Created
                    </Typography>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CalendarIcon fontSize="small" color="action" />
                      <Typography variant="body2">
                        {format(new Date(task.created_at), 'MMM d, yyyy h:mm a')}
                      </Typography>
                    </Stack>
                  </Box>

                  {/* Updated At */}
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Last Updated
                    </Typography>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <UpdateIcon fontSize="small" color="action" />
                      <Typography variant="body2">
                        {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true })}
                      </Typography>
                    </Stack>
                  </Box>

                  {/* Completed At */}
                  {task.completed_at && (
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Completed
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <CheckCircleIcon fontSize="small" color="success" />
                        <Typography variant="body2">
                          {format(new Date(task.completed_at), 'MMM d, yyyy h:mm a')}
                        </Typography>
                      </Stack>
                    </Box>
                  )}
                </Stack>
              </Grid>
            </Grid>

            {/* Tags */}
            {task.tags && task.tags.length > 0 && (
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Tags
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {task.tags.map((tag) => (
                    <Chip key={tag} label={tag} size="small" />
                  ))}
                </Stack>
              </Box>
            )}

            {/* Subtasks */}
            {task.subtask_count && task.subtask_count > 0 && (
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Subtasks
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {task.subtask_count} subtask{task.subtask_count > 1 ? 's' : ''}
                </Typography>
              </Box>
            )}
          </Stack>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* Attachments Tab */}
          <TaskAttachments taskId={task.id} />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* Activity Tab - Coming Soon */}
          <Box textAlign="center" py={4}>
            <Typography variant="body2" color="text.secondary">
              Activity tracking coming soon...
            </Typography>
          </Box>
        </TabPanel>
      </DialogContent>

      <Divider />

      <DialogActions sx={{ p: 2 }}>
        <Stack direction="row" spacing={1} sx={{ flex: 1 }}>
          {/* Left side actions */}
          <Box>
            {canModify && (
              <Tooltip title={task.status === 'completed' ? 'Mark as incomplete' : 'Mark as complete'}>
                <Button
                  startIcon={task.status === 'completed' ? <UncheckedIcon /> : <CheckCircleIcon />}
                  onClick={onToggleStatus}
                  color={task.status === 'completed' ? 'inherit' : 'success'}
                >
                  {task.status === 'completed' ? 'Uncomplete' : 'Complete'}
                </Button>
              </Tooltip>
            )}
          </Box>

          {/* Right side actions */}
          <Box sx={{ ml: 'auto' }} display="flex" gap={1}>
            {canModify && (
              <>
                <Button startIcon={<EditIcon />} onClick={onEdit} variant="outlined">
                  Edit
                </Button>
                {onArchive && (
                  <Tooltip title="Archive task">
                    <Button
                      startIcon={<ArchiveIcon />}
                      onClick={onArchive}
                      color="warning"
                      variant="outlined"
                    >
                      Archive
                    </Button>
                  </Tooltip>
                )}
              </>
            )}
            {task.status === 'archived' && onUnarchive && (
              <Tooltip title="Restore task">
                <Button
                  startIcon={<UnarchiveIcon />}
                  onClick={onUnarchive}
                  color="primary"
                  variant="outlined"
                >
                  Restore
                </Button>
              </Tooltip>
            )}
            <Tooltip title="Delete task permanently">
              <Button startIcon={<DeleteIcon />} onClick={onDelete} color="error">
                Delete
              </Button>
            </Tooltip>
          </Box>
        </Stack>
      </DialogActions>
    </Dialog>
  );
}