import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  IconButton,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  CircularProgress,
  Chip,
  Stack,
  Menu,
  MenuItem,
  FormControlLabel,
  Switch,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  MoreVert as MoreIcon,
  List as ListIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';

import { listService } from '../services/listService';
import { workspaceService } from '../services/workspaceService';
import type { List, ListCreate, ListUpdate } from '../types';

export default function Lists() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  // State
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingList, setEditingList] = useState<List | null>(null);
  const [listName, setListName] = useState('');
  const [listIcon, setListIcon] = useState('📋');
  const [listColor, setListColor] = useState('#3f51b5');
  const [isDefault, setIsDefault] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedList, setSelectedList] = useState<List | null>(null);

  // Queries
  const { data: workspace, isLoading: workspaceLoading } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => workspaceService.getWorkspace(workspaceId!),
    enabled: !!workspaceId,
  });

  const { data: lists, isLoading: listsLoading } = useQuery({
    queryKey: ['lists', workspaceId],
    queryFn: () => listService.getListsByWorkspace(workspaceId!),
    enabled: !!workspaceId,
  });

  // Mutations
  const createListMutation = useMutation({
    mutationFn: (data: ListCreate) => listService.createList(workspaceId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lists', workspaceId] });
      enqueueSnackbar('List created successfully', { variant: 'success' });
      handleCloseDialog();
    },
    onError: (error: any) => {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to create list', {
        variant: 'error',
      });
    },
  });

  const updateListMutation = useMutation({
    mutationFn: ({ listId, data }: { listId: string; data: ListUpdate }) =>
      listService.updateList(workspaceId!, listId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lists', workspaceId] });
      enqueueSnackbar('List updated successfully', { variant: 'success' });
      handleCloseDialog();
    },
    onError: (error: any) => {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to update list', {
        variant: 'error',
      });
    },
  });

  const deleteListMutation = useMutation({
    mutationFn: (listId: string) => listService.deleteList(workspaceId!, listId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lists', workspaceId] });
      enqueueSnackbar('List deleted successfully', { variant: 'success' });
    },
    onError: (error: any) => {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to delete list', {
        variant: 'error',
      });
    },
  });

  // Handlers
  const handleOpenDialog = (list?: List) => {
    if (list) {
      setEditingList(list);
      setListName(list.name);
      setListIcon(list.icon || '📋');
      setListColor(list.color || '#3f51b5');
      setIsDefault(list.is_default || false);
    } else {
      setEditingList(null);
      setListName('');
      setListIcon('📋');
      setListColor('#3f51b5');
      setIsDefault(false);
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingList(null);
    setListName('');
    setListIcon('📋');
    setListColor('#3f51b5');
    setIsDefault(false);
  };

  const handleSaveList = async () => {
    if (!listName.trim()) {
      enqueueSnackbar('List name is required', { variant: 'error' });
      return;
    }

    const data = {
      name: listName.trim(),
      icon: listIcon,
      color: listColor,
      is_default: isDefault,
    };

    if (editingList) {
      await updateListMutation.mutateAsync({
        listId: editingList.id,
        data,
      });
    } else {
      await createListMutation.mutateAsync(data);
    }
  };

  const handleDeleteList = async (list: List) => {
    if (list.is_default) {
      enqueueSnackbar('Cannot delete the default list', { variant: 'error' });
      return;
    }

    if (window.confirm(`Are you sure you want to delete "${list.name}"? This action cannot be undone.`)) {
      await deleteListMutation.mutateAsync(list.id);
    }
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, list: List) => {
    setMenuAnchor(event.currentTarget);
    setSelectedList(list);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setSelectedList(null);
  };

  if (!workspaceId) {
    return (
      <Box p={3}>
        <Typography variant="h6">No workspace selected</Typography>
      </Box>
    );
  }

  if (workspaceLoading || listsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box mb={3} display="flex" alignItems="center" gap={2}>
        <IconButton onClick={() => navigate('/workspaces')}>
          <ArrowBackIcon />
        </IconButton>
        <Box flex={1}>
          <Typography variant="h4">
            {workspace?.emoji} {workspace?.name} - Lists
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage lists for organizing your tasks
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Create List
        </Button>
      </Box>

      <Grid container spacing={3}>
        {lists?.map((list) => (
          <Grid item xs={12} sm={6} md={4} key={list.id}>
            <Card
              sx={{ cursor: 'pointer', transition: 'box-shadow 0.2s', '&:hover': { boxShadow: 4 } }}
              onClick={() => navigate(`/workspaces/${workspaceId}/lists/${list.id}/tasks`)}
              tabIndex={0}
              role="button"
              aria-label={`View tasks in ${list.name}`}
            >
              <CardContent>
                <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                  <Box>
                    <Typography variant="h6" display="flex" alignItems="center" gap={1}>
                      {list.icon} {list.name}
                      {list.is_default && (
                        <Chip label="Default" size="small" color="primary" />
                      )}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {list.task_count || 0} tasks
                    </Typography>
                  </Box>
                  <IconButton
                    size="small"
                    onClick={(e) => { e.stopPropagation(); handleMenuClick(e, list); }}
                  >
                    <MoreIcon />
                  </IconButton>
                </Box>
              </CardContent>
              <CardActions>
                <Button
                  size="small"
                  onClick={(e) => { e.stopPropagation(); navigate(`/workspaces/${workspaceId}/lists/${list.id}/tasks`); }}
                >
                  View Tasks
                </Button>
                <Button
                  size="small"
                  onClick={(e) => { e.stopPropagation(); handleOpenDialog(list); }}
                  disabled={list.is_default}
                >
                  Edit
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingList ? 'Edit List' : 'Create New List'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <TextField
              label="List Name"
              value={listName}
              onChange={(e) => setListName(e.target.value)}
              fullWidth
              required
              autoFocus
            />

            <Box>
              <FormControlLabel
                control={
                  <Switch
                    checked={isDefault}
                    onChange={(e) => setIsDefault(e.target.checked)}
                    disabled={editingList?.is_default}
                  />
                }
                label="Set as default list for this workspace"
              />
              <Typography variant="caption" color="text.secondary" display="block" sx={{ ml: 2 }}>
                Tasks created by AI will use the default list when no specific list is mentioned
              </Typography>
            </Box>

            <TextField
              label="Icon (Emoji)"
              value={listIcon}
              onChange={(e) => setListIcon(e.target.value)}
              fullWidth
              inputProps={{ maxLength: 2 }}
              helperText="Choose an emoji icon for your list"
            />

            <TextField
              label="Color"
              type="color"
              value={listColor}
              onChange={(e) => setListColor(e.target.value)}
              fullWidth
              helperText="Choose a color for your list"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSaveList}
            variant="contained"
            disabled={createListMutation.isPending || updateListMutation.isPending}
          >
            {editingList ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* List Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem
          onClick={() => {
            if (selectedList) {
              navigate(`/workspaces/${workspaceId}/lists/${selectedList.id}/tasks`);
            }
            handleMenuClose();
          }}
        >
          <ListIcon sx={{ mr: 1 }} />
          View Tasks
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (selectedList) {
              handleOpenDialog(selectedList);
            }
            handleMenuClose();
          }}
          disabled={selectedList?.is_default}
        >
          <EditIcon sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (selectedList) {
              handleDeleteList(selectedList);
            }
            handleMenuClose();
          }}
          disabled={selectedList?.is_default}
        >
          <DeleteIcon sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>
    </Box>
  );
}