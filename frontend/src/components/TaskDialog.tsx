import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Chip,
  IconButton,
  Stack,
  FormHelperText,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { Close as CloseIcon } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { useSnackbar } from 'notistack';

import type { Task, TaskCreate, TaskUpdate, Workspace, List } from '../types';
import { listService } from '../services/listService';

interface TaskDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: TaskCreate | TaskUpdate) => Promise<void>;
  task?: Task;
  workspaces: Workspace[];
  defaultWorkspaceId?: string;
}

export default function TaskDialog({
  open,
  onClose,
  onSave,
  task,
  workspaces,
  defaultWorkspaceId,
}: TaskDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const [isLoading, setIsLoading] = useState(false);
  const [tags, setTags] = useState<string[]>(task?.tags || []);
  const [tagInput, setTagInput] = useState('');
  const [lists, setLists] = useState<List[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>(defaultWorkspaceId || '');
  const [loadingLists, setLoadingLists] = useState(false);

  const {
    control,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<TaskCreate & { list_id?: string }>({
    defaultValues: {
      title: '',
      description: '',
      workspace_id: defaultWorkspaceId || '',
      list_id: undefined,
      priority: 'medium',
      status: 'todo',
      due_date: undefined,
      reminder_date: undefined,
    },
  });

  const watchedWorkspaceId = watch('workspace_id');

  useEffect(() => {
    if (task) {
      reset({
        title: task.title,
        description: task.description,
        priority: task.priority,
        status: task.status,
        due_date: task.due_date,
        reminder_date: task.reminder_date,
        list_id: task.list_id,
      });
      setTags(task.tags || []);
      // For editing, we don't change workspace - keep the existing one
      setSelectedWorkspaceId('');
    } else {
      reset({
        title: '',
        description: '',
        workspace_id: defaultWorkspaceId || '',
        list_id: undefined,
        priority: 'medium',
        status: 'todo',
        due_date: undefined,
        reminder_date: undefined,
      });
      setTags([]);
      setSelectedWorkspaceId(defaultWorkspaceId || '');
    }
  }, [task, defaultWorkspaceId, reset]);

  // Fetch lists when workspace changes
  useEffect(() => {
    if (watchedWorkspaceId) {
      setSelectedWorkspaceId(watchedWorkspaceId);
      setLoadingLists(true);
      listService.getListsByWorkspace(watchedWorkspaceId)
        .then((fetchedLists) => {
          setLists(fetchedLists);
          // If no list is selected and there's a default list, select it
          const defaultList = fetchedLists.find(list => list.is_default);
          if (!watch('list_id') && defaultList) {
            setValue('list_id', defaultList.id);
          }
        })
        .catch((error) => {
          console.error('Failed to fetch lists:', error);
          enqueueSnackbar('Failed to load lists', { variant: 'error' });
        })
        .finally(() => {
          setLoadingLists(false);
        });
    } else {
      setLists([]);
      setValue('list_id', undefined);
    }
  }, [watchedWorkspaceId, setValue, watch, enqueueSnackbar]);

  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const onSubmit = async (data: TaskCreate & { list_id?: string } | TaskUpdate) => {
    setIsLoading(true);
    try {
      await onSave({ ...data, tags });
      enqueueSnackbar(task ? 'Task updated successfully' : 'Task created successfully', {
        variant: 'success',
      });
      onClose();
    } catch (error: any) {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to save task', {
        variant: 'error',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogTitle>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            {task ? 'Edit Task' : 'Create New Task'}
            <IconButton size="small" onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        
        <DialogContent dividers>
          <Stack spacing={3}>
            <Controller
              name="title"
              control={control}
              rules={{ required: 'Title is required' }}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Title"
                  fullWidth
                  error={!!errors.title}
                  helperText={errors.title?.message}
                  autoFocus
                />
              )}
            />

            <Controller
              name="description"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Description"
                  fullWidth
                  multiline
                  rows={3}
                />
              )}
            />

            {!task && (
              <>
                <Controller
                  name="workspace_id"
                  control={control}
                  rules={{ required: 'Workspace is required' }}
                  render={({ field }) => (
                    <FormControl fullWidth error={!!errors.workspace_id}>
                      <InputLabel>Workspace</InputLabel>
                      <Select {...field} label="Workspace">
                        {workspaces.map((workspace) => (
                          <MenuItem key={workspace.id} value={workspace.id}>
                            {workspace.emoji} {workspace.name}
                          </MenuItem>
                        ))}
                      </Select>
                      {errors.workspace_id && (
                        <FormHelperText>{errors.workspace_id.message}</FormHelperText>
                      )}
                    </FormControl>
                  )}
                />
                
                {selectedWorkspaceId && (
                  <Controller
                    name="list_id"
                    control={control}
                    rules={{ required: 'List is required' }}
                    render={({ field }) => (
                      <FormControl fullWidth error={!!errors.list_id} disabled={loadingLists}>
                        <InputLabel>List</InputLabel>
                        <Select {...field} label="List">
                          {lists.map((list) => (
                            <MenuItem key={list.id} value={list.id}>
                              {list.icon} {list.name}
                              {list.is_default && (
                                <Chip
                                  label="Default"
                                  size="small"
                                  sx={{ ml: 1 }}
                                />
                              )}
                            </MenuItem>
                          ))}
                        </Select>
                        {errors.list_id && (
                          <FormHelperText>{errors.list_id.message}</FormHelperText>
                        )}
                        {loadingLists && (
                          <FormHelperText>Loading lists...</FormHelperText>
                        )}
                      </FormControl>
                    )}
                  />
                )}
              </>
            )}

            <Box display="flex" gap={2}>
              <Controller
                name="priority"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>Priority</InputLabel>
                    <Select {...field} label="Priority">
                      <MenuItem value="low">Low</MenuItem>
                      <MenuItem value="medium">Medium</MenuItem>
                      <MenuItem value="high">High</MenuItem>
                    </Select>
                  </FormControl>
                )}
              />

              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>Status</InputLabel>
                    <Select {...field} label="Status">
                      <MenuItem value="todo">To Do</MenuItem>
                      <MenuItem value="in_progress">In Progress</MenuItem>
                      <MenuItem value="completed">Completed</MenuItem>
                      <MenuItem value="archived">Archived</MenuItem>
                    </Select>
                  </FormControl>
                )}
              />
            </Box>

            <Box display="flex" gap={2}>
              <Controller
                name="due_date"
                control={control}
                render={({ field }) => (
                  <DateTimePicker
                    {...field}
                    label="Due Date"
                    value={field.value ? new Date(field.value) : null}
                    onChange={(date) => field.onChange(date?.toISOString())}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                      },
                    }}
                  />
                )}
              />

              <Controller
                name="reminder_date"
                control={control}
                render={({ field }) => (
                  <DateTimePicker
                    {...field}
                    label="Reminder"
                    value={field.value ? new Date(field.value) : null}
                    onChange={(date) => field.onChange(date?.toISOString())}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                      },
                    }}
                  />
                )}
              />
            </Box>

            <Box>
              <TextField
                label="Add Tag"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
                fullWidth
                size="small"
                placeholder="Press Enter to add tag"
              />
              <Box mt={1} display="flex" gap={0.5} flexWrap="wrap">
                {tags.map((tag) => (
                  <Chip
                    key={tag}
                    label={tag}
                    size="small"
                    onDelete={() => handleRemoveTag(tag)}
                  />
                ))}
              </Box>
            </Box>
          </Stack>
        </DialogContent>

        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={isLoading}>
            {task ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}