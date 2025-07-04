import { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Fab,
  Tab,
  Tabs,
  TextField,
  InputAdornment,
  IconButton,
  CircularProgress,
  Paper,
  Button,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  Clear as ClearIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { useNavigate } from 'react-router-dom';
import { useDebounce } from 'use-debounce';

import WorkspaceCard from '../components/WorkspaceCard';
import WorkspaceDialog from '../components/WorkspaceDialog';
import MembersDialog from '../components/MembersDialog';
import { workspaceService } from '../services/workspaceService';
import { useAuthStore } from '../store/authStore';
import type { Workspace, WorkspaceCreate, WorkspaceUpdate } from '../types';

export default function Workspaces() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  
  // State
  const [tab, setTab] = useState<'all' | 'personal' | 'team'>('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 300);
  const [workspaceDialogOpen, setWorkspaceDialogOpen] = useState(false);
  const [editingWorkspace, setEditingWorkspace] = useState<Workspace | undefined>();
  const [membersDialogOpen, setMembersDialogOpen] = useState(false);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);

  // Queries
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['workspaces', tab, debouncedSearch],
    queryFn: () => {
      const params: any = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (tab !== 'all') params.type = tab;
      return workspaceService.getWorkspaces(params);
    },
  });

  const workspaces = data || [];

  // Mutations
  const createWorkspaceMutation = useMutation({
    mutationFn: (data: WorkspaceCreate) => workspaceService.createWorkspace(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  const updateWorkspaceMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: WorkspaceUpdate }) =>
      workspaceService.updateWorkspace(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
  });

  const deleteWorkspaceMutation = useMutation({
    mutationFn: (id: string) => workspaceService.deleteWorkspace(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  const leaveWorkspaceMutation = useMutation({
    mutationFn: (id: string) => workspaceService.leaveWorkspace(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
  });

  // Handlers
  const handleCreateWorkspace = () => {
    setEditingWorkspace(undefined);
    setWorkspaceDialogOpen(true);
  };

  const handleEditWorkspace = (workspace: Workspace) => {
    setEditingWorkspace(workspace);
    setWorkspaceDialogOpen(true);
  };

  const handleSaveWorkspace = async (data: WorkspaceCreate | WorkspaceUpdate) => {
    if (editingWorkspace) {
      await updateWorkspaceMutation.mutateAsync({ id: editingWorkspace.id, data: data as WorkspaceUpdate });
    } else {
      const result = await createWorkspaceMutation.mutateAsync(data as WorkspaceCreate);
      // Navigate to the new workspace
      navigate(`/tasks?workspace=${result.id}`);
    }
  };

  const handleDeleteWorkspace = async (workspace: Workspace) => {
    if (
      window.confirm(
        `Are you sure you want to delete "${workspace.name}"? This will delete all tasks in this workspace.`
      )
    ) {
      try {
        await deleteWorkspaceMutation.mutateAsync(workspace.id);
        enqueueSnackbar('Workspace deleted successfully', { variant: 'success' });
      } catch (error: any) {
        enqueueSnackbar(error.response?.data?.detail || 'Failed to delete workspace', {
          variant: 'error',
        });
      }
    }
  };

  const handleLeaveWorkspace = async (workspace: Workspace) => {
    if (
      window.confirm(
        `Are you sure you want to leave "${workspace.name}"? You will need to be invited again to access it.`
      )
    ) {
      try {
        await leaveWorkspaceMutation.mutateAsync(workspace.id);
        enqueueSnackbar('Left workspace successfully', { variant: 'success' });
      } catch (error: any) {
        enqueueSnackbar(error.response?.data?.detail || 'Failed to leave workspace', {
          variant: 'error',
        });
      }
    }
  };

  const handleManageMembers = (workspace: Workspace) => {
    setSelectedWorkspace(workspace);
    setMembersDialogOpen(true);
  };

  const handleWorkspaceClick = (workspace: Workspace) => {
    navigate(`/workspaces/${workspace.id}/lists`);
  };

  const handleManageLists = (workspace: Workspace) => {
    navigate(`/workspaces/${workspace.id}/lists`);
  };

  const filteredWorkspaces = workspaces.filter((workspace) => {
    if (tab === 'personal' && workspace.type !== 'personal') return false;
    if (tab === 'team' && workspace.type !== 'team') return false;
    return true;
  });

  return (
    <Box>
      <Box mb={3}>
        <Typography variant="h4" gutterBottom>
          Workspaces
        </Typography>

        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <TextField
            placeholder="Search workspaces..."
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

          <IconButton onClick={() => refetch()}>
            <RefreshIcon />
          </IconButton>
        </Box>

        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="All Workspaces" value="all" />
          <Tab label="Personal" value="personal" />
          <Tab label="Team" value="team" />
        </Tabs>
      </Box>

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      ) : filteredWorkspaces.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No workspaces found
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={2}>
            {search
              ? 'Try adjusting your search'
              : tab === 'personal'
              ? 'Create your personal workspace to get started'
              : tab === 'team'
              ? 'Create or join a team workspace'
              : 'Create your first workspace to organize your tasks'}
          </Typography>
          <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreateWorkspace}>
            Create Workspace
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {filteredWorkspaces.map((workspace) => (
            <Grid item xs={12} sm={6} md={4} key={workspace.id}>
              <WorkspaceCard
                workspace={workspace}
                onEdit={handleEditWorkspace}
                onDelete={handleDeleteWorkspace}
                onManageMembers={handleManageMembers}
                onManageLists={handleManageLists}
                onLeave={workspace.owner_id !== user?.id ? handleLeaveWorkspace : undefined}
                isOwner={workspace.owner_id === user?.id}
                onClick={() => handleWorkspaceClick(workspace)}
              />
            </Grid>
          ))}
        </Grid>
      )}

      <Fab
        color="primary"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={handleCreateWorkspace}
      >
        <AddIcon />
      </Fab>

      <WorkspaceDialog
        open={workspaceDialogOpen}
        onClose={() => setWorkspaceDialogOpen(false)}
        onSave={handleSaveWorkspace}
        workspace={editingWorkspace}
      />

      {selectedWorkspace && user && (
        <MembersDialog
          open={membersDialogOpen}
          onClose={() => setMembersDialogOpen(false)}
          workspace={selectedWorkspace}
          currentUserId={user.id}
        />
      )}
    </Box>
  );
}