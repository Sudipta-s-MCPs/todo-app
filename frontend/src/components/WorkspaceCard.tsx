import { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Chip,
} from '@mui/material';
import {
  MoreVert as MoreIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  People as PeopleIcon,
  Task as TaskIcon,
  ExitToApp as LeaveIcon,
  List as ListIcon,
} from '@mui/icons-material';

import type { Workspace } from '../types';

interface WorkspaceCardProps {
  workspace: Workspace;
  onEdit: (workspace: Workspace) => void;
  onDelete: (workspace: Workspace) => void;
  onManageMembers: (workspace: Workspace) => void;
  onManageLists: (workspace: Workspace) => void;
  onLeave?: (workspace: Workspace) => void;
  isOwner: boolean;
  onClick?: () => void;
}

export default function WorkspaceCard({
  workspace,
  onEdit,
  onDelete,
  onManageMembers,
  onManageLists,
  onLeave,
  isOwner,
  onClick,
}: WorkspaceCardProps) {
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
    onEdit(workspace);
  };

  const handleDelete = () => {
    handleMenuClose();
    onDelete(workspace);
  };

  const handleManageMembers = () => {
    handleMenuClose();
    onManageMembers(workspace);
  };

  const handleManageLists = () => {
    handleMenuClose();
    onManageLists(workspace);
  };

  const handleLeave = () => {
    handleMenuClose();
    onLeave?.(workspace);
  };

  return (
    <Card
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': {
          boxShadow: onClick ? 4 : 2,
        },
      }}
      onClick={onClick}
    >
      <CardContent>
        <Box display="flex" alignItems="flex-start" justifyContent="space-between">
          <Box flex={1}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <Typography variant="h5" component="span">
                {workspace.emoji || '📁'}
              </Typography>
              <Typography variant="h6" component="h3">
                {workspace.name}
              </Typography>
              {workspace.type === 'personal' && (
                <Chip label="Personal" size="small" color="primary" />
              )}
            </Box>

            {workspace.description && (
              <Typography variant="body2" color="text.secondary" mb={2}>
                {workspace.description}
              </Typography>
            )}

            <Box display="flex" alignItems="center" gap={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <TaskIcon fontSize="small" color="action" />
                <Typography variant="body2" color="text.secondary">
                  {workspace.task_count || 0} tasks
                </Typography>
              </Box>

              {workspace.type === 'shared' && (
                <Box display="flex" alignItems="center" gap={1}>
                  <PeopleIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="text.secondary">
                    {workspace.member_count || 0} members
                  </Typography>
                </Box>
              )}
            </Box>
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
          {isOwner && (
            <MenuItem onClick={handleEdit}>
              <EditIcon fontSize="small" sx={{ mr: 1 }} />
              Edit
            </MenuItem>
          )}
          
          <MenuItem onClick={handleManageLists}>
            <ListIcon fontSize="small" sx={{ mr: 1 }} />
            Manage Lists
          </MenuItem>
          
          {workspace.type === 'shared' && isOwner && (
            <MenuItem onClick={handleManageMembers}>
              <PeopleIcon fontSize="small" sx={{ mr: 1 }} />
              Manage Members
            </MenuItem>
          )}
          
          {workspace.type === 'shared' && !isOwner && onLeave && (
            <MenuItem onClick={handleLeave}>
              <LeaveIcon fontSize="small" sx={{ mr: 1 }} />
              Leave Workspace
            </MenuItem>
          )}
          
          {isOwner && (
            <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
              <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
              Delete
            </MenuItem>
          )}
        </Menu>
      </CardContent>
    </Card>
  );
}