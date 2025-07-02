import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Avatar,
  Select,
  MenuItem,
  Typography,
  CircularProgress,
  InputAdornment,
  Chip,
} from '@mui/material';
import {
  Close as CloseIcon,
  PersonAdd as PersonAddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';

import { workspaceService } from '../services/workspaceService';
import type { Workspace, WorkspaceMember } from '../types';

interface MembersDialogProps {
  open: boolean;
  onClose: () => void;
  workspace: Workspace;
  currentUserId: string;
}

export default function MembersDialog({
  open,
  onClose,
  workspace,
  currentUserId,
}: MembersDialogProps) {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'viewer' | 'member' | 'admin'>('member');
  const [isInviting, setIsInviting] = useState(false);

  const { data: members, isLoading } = useQuery({
    queryKey: ['workspace-members', workspace.id],
    queryFn: () => workspaceService.getWorkspaceMembers(workspace.id),
    enabled: open,
  });

  const inviteMemberMutation = useMutation({
    mutationFn: ({ email, role }: { email: string; role: 'viewer' | 'member' | 'admin' }) =>
      workspaceService.inviteMember(workspace.id, email, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', workspace.id] });
      setEmail('');
      enqueueSnackbar('Member invited successfully', { variant: 'success' });
    },
    onError: (error: any) => {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to invite member', {
        variant: 'error',
      });
    },
  });

  const updateMemberRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: 'viewer' | 'member' | 'admin' }) =>
      workspaceService.updateMemberRole(workspace.id, userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', workspace.id] });
      enqueueSnackbar('Member role updated', { variant: 'success' });
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: (userId: string) =>
      workspaceService.removeMember(workspace.id, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', workspace.id] });
      enqueueSnackbar('Member removed', { variant: 'success' });
    },
  });

  const handleInvite = async () => {
    if (!email.trim()) return;
    
    setIsInviting(true);
    try {
      await inviteMemberMutation.mutateAsync({ email, role });
    } finally {
      setIsInviting(false);
    }
  };

  const handleRoleChange = async (member: WorkspaceMember, newRole: 'viewer' | 'member' | 'admin') => {
    if (member.role === newRole) return;
    await updateMemberRoleMutation.mutateAsync({ userId: member.user_id, role: newRole });
  };

  const handleRemove = async (member: WorkspaceMember) => {
    if (window.confirm(`Remove ${member.user?.name || 'this member'} from the workspace?`)) {
      await removeMemberMutation.mutateAsync(member.user_id);
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'primary';
      case 'member':
        return 'default';
      case 'viewer':
        return 'secondary';
      default:
        return 'default';
    }
  };

  const isOwner = workspace.owner_id === currentUserId;
  const currentMember = members?.find((m) => m.user_id === currentUserId);
  const canManageMembers = isOwner || currentMember?.role === 'admin';

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">
            {workspace.emoji} {workspace.name} - Members
          </Typography>
          <IconButton size="small" onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {canManageMembers && (
          <Box mb={3}>
            <Typography variant="subtitle2" gutterBottom>
              Invite New Member
            </Typography>
            <Box display="flex" gap={1}>
              <TextField
                placeholder="Enter email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleInvite();
                  }
                }}
                size="small"
                fullWidth
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <PersonAddIcon />
                    </InputAdornment>
                  ),
                }}
              />
              <Select
                value={role}
                onChange={(e) => setRole(e.target.value as 'viewer' | 'member' | 'admin')}
                size="small"
                sx={{ minWidth: 100 }}
              >
                <MenuItem value="viewer">Viewer</MenuItem>
                <MenuItem value="member">Member</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </Select>
              <Button
                variant="contained"
                onClick={handleInvite}
                disabled={!email.trim() || isInviting}
                startIcon={isInviting ? <CircularProgress size={16} /> : <PersonAddIcon />}
              >
                Invite
              </Button>
            </Box>
          </Box>
        )}

        {isLoading ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : (
          <List>
            {members?.map((member) => (
              <ListItem key={member.id} divider>
                <ListItemAvatar>
                  <Avatar src={member.user?.avatar_url}>
                    {member.user?.name.charAt(0).toUpperCase()}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      {member.user?.name}
                      {member.user_id === workspace.owner_id && (
                        <Chip label="Owner" size="small" color="primary" />
                      )}
                      {member.user_id === currentUserId && (
                        <Chip label="You" size="small" />
                      )}
                    </Box>
                  }
                  secondary={member.user?.email}
                />
                <ListItemSecondaryAction>
                  <Box display="flex" alignItems="center" gap={1}>
                    {canManageMembers && member.user_id !== workspace.owner_id ? (
                      <Select
                        value={member.role}
                        onChange={(e) =>
                          handleRoleChange(member, e.target.value as 'viewer' | 'member' | 'admin')
                        }
                        size="small"
                        variant="standard"
                      >
                        <MenuItem value="viewer">Viewer</MenuItem>
                        <MenuItem value="member">Member</MenuItem>
                        <MenuItem value="admin">Admin</MenuItem>
                      </Select>
                    ) : (
                      <Chip
                        label={member.role}
                        size="small"
                        color={getRoleColor(member.role)}
                      />
                    )}
                    
                    {canManageMembers &&
                      member.user_id !== workspace.owner_id &&
                      member.user_id !== currentUserId && (
                        <IconButton
                          size="small"
                          onClick={() => handleRemove(member)}
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      )}
                  </Box>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}