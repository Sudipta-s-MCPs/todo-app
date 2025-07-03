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
  IconButton,
  Stack,
  Typography,
  Popover,
  Grid,
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { useSnackbar } from 'notistack';

import type { Workspace, WorkspaceCreate, WorkspaceUpdate } from '../types';

interface WorkspaceDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: WorkspaceCreate | WorkspaceUpdate) => Promise<void>;
  workspace?: Workspace;
}

const EMOJI_OPTIONS = [
  '📁', '💼', '🎯', '🚀', '💡', '📊', '🎨', '📚',
  '🏠', '🌟', '🔧', '🎪', '🌈', '🎮', '🎬', '🎵',
];

const COLOR_OPTIONS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#F7DC6F', '#BB8FCE',
  '#85C1E2', '#F8B739', '#52C41A', '#1890FF', '#722ED1',
];

export default function WorkspaceDialog({
  open,
  onClose,
  onSave,
  workspace,
}: WorkspaceDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const [isLoading, setIsLoading] = useState(false);
  const [emojiAnchor, setEmojiAnchor] = useState<HTMLElement | null>(null);
  const [colorAnchor, setColorAnchor] = useState<HTMLElement | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<WorkspaceCreate | WorkspaceUpdate>({
    defaultValues: {
      name: '',
      description: '',
      type: 'team',
      emoji: '📁',
      color: '#1890FF',
    },
  });

  const selectedEmoji = watch('emoji');
  const selectedColor = watch('color');

  useEffect(() => {
    if (workspace) {
      reset({
        name: workspace.name,
        description: workspace.description,
        emoji: workspace.emoji || '📁',
        color: workspace.color || '#1890FF',
      });
    } else {
      reset({
        name: '',
        description: '',
        type: 'team',
        emoji: '📁',
        color: '#1890FF',
      });
    }
  }, [workspace, reset]);

  const onSubmit = async (data: WorkspaceCreate | WorkspaceUpdate) => {
    setIsLoading(true);
    try {
      await onSave(data);
      enqueueSnackbar(
        workspace ? 'Workspace updated successfully' : 'Workspace created successfully',
        { variant: 'success' }
      );
      onClose();
    } catch (error: any) {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to save workspace', {
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
            {workspace ? 'Edit Workspace' : 'Create New Workspace'}
            <IconButton size="small" onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent dividers>
          <Stack spacing={3}>
            <Box display="flex" gap={2} alignItems="flex-start">
              <Box>
                <Typography variant="caption" color="text.secondary" gutterBottom>
                  Icon
                </Typography>
                <Button
                  variant="outlined"
                  sx={{
                    width: 64,
                    height: 64,
                    fontSize: '2rem',
                    minWidth: 'auto',
                  }}
                  onClick={(e) => setEmojiAnchor(e.currentTarget)}
                >
                  {selectedEmoji}
                </Button>
              </Box>

              <Box flex={1}>
                <Controller
                  name="name"
                  control={control}
                  rules={{ required: 'Name is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Name"
                      fullWidth
                      error={!!errors.name}
                      helperText={errors.name?.message}
                      autoFocus
                    />
                  )}
                />
              </Box>
            </Box>

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
                  placeholder="What is this workspace for?"
                />
              )}
            />

            {!workspace && (
              <Controller
                name="type"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>Type</InputLabel>
                    <Select {...field} label="Type">
                      <MenuItem value="personal">Personal</MenuItem>
                      <MenuItem value="team">Team</MenuItem>
                    </Select>
                  </FormControl>
                )}
              />
            )}

            <Box>
              <Typography variant="caption" color="text.secondary" gutterBottom>
                Color Theme
              </Typography>
              <Box display="flex" gap={1} mt={1}>
                {COLOR_OPTIONS.slice(0, 8).map((color) => (
                  <Box
                    key={color}
                    sx={{
                      width: 32,
                      height: 32,
                      borderRadius: 1,
                      backgroundColor: color,
                      cursor: 'pointer',
                      border: selectedColor === color ? '2px solid' : 'none',
                      borderColor: 'text.primary',
                    }}
                    onClick={() => setValue('color', color)}
                  />
                ))}
                <Button
                  variant="outlined"
                  size="small"
                  sx={{ minWidth: 'auto', px: 1 }}
                  onClick={(e) => setColorAnchor(e.currentTarget)}
                >
                  More
                </Button>
              </Box>
            </Box>
          </Stack>
        </DialogContent>

        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={isLoading}>
            {workspace ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </form>

      {/* Emoji Picker Popover */}
      <Popover
        open={Boolean(emojiAnchor)}
        anchorEl={emojiAnchor}
        onClose={() => setEmojiAnchor(null)}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
      >
        <Box sx={{ p: 2, maxWidth: 280 }}>
          <Grid container spacing={1}>
            {EMOJI_OPTIONS.map((emoji) => (
              <Grid item key={emoji}>
                <Button
                  variant={selectedEmoji === emoji ? 'contained' : 'outlined'}
                  sx={{
                    minWidth: 'auto',
                    width: 48,
                    height: 48,
                    fontSize: '1.5rem',
                  }}
                  onClick={() => {
                    setValue('emoji', emoji);
                    setEmojiAnchor(null);
                  }}
                >
                  {emoji}
                </Button>
              </Grid>
            ))}
          </Grid>
        </Box>
      </Popover>

      {/* Color Picker Popover */}
      <Popover
        open={Boolean(colorAnchor)}
        anchorEl={colorAnchor}
        onClose={() => setColorAnchor(null)}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
      >
        <Box sx={{ p: 2, maxWidth: 240 }}>
          <Grid container spacing={1}>
            {COLOR_OPTIONS.map((color) => (
              <Grid item key={color}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: 1,
                    backgroundColor: color,
                    cursor: 'pointer',
                    border: selectedColor === color ? '2px solid' : 'none',
                    borderColor: 'text.primary',
                  }}
                  onClick={() => {
                    setValue('color', color);
                    setColorAnchor(null);
                  }}
                />
              </Grid>
            ))}
          </Grid>
        </Box>
      </Popover>
    </Dialog>
  );
}