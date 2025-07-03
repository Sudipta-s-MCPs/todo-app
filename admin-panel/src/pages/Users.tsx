import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Button,
  Chip,
  IconButton,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Checkbox,
  Alert,
} from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams, GridPaginationModel } from '@mui/x-data-grid'
import {
  Add as AddIcon,
  Search as SearchIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Block as BlockIcon,
  CheckCircle as ActiveIcon,
  CheckCircle,
} from '@mui/icons-material'
import { format } from 'date-fns'
import { api } from '../services/api'

interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  is_admin: boolean
  is_approved: boolean
  approval_status: string
  mfa_enabled: boolean
  created_at: string
  last_login_at: string | null
  workspace_count: number
  task_count: number
  device_count: number
  api_key_count: number
  mcp_agent_count: number
}

export default function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [openDialog, setOpenDialog] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [error, setError] = useState('')
  const [totalUsers, setTotalUsers] = useState(0)
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  })
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    password: '',
    is_admin: false,
  })

  useEffect(() => {
    fetchUsers()
  }, [paginationModel, searchQuery])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const response = await api.get('/admin/users', {
        params: {
          skip: paginationModel.page * paginationModel.pageSize,
          limit: paginationModel.pageSize,
          search: searchQuery || undefined,
        }
      })
      setUsers(response.data.users)
      setTotalUsers(response.data.total)
    } catch (error) {
      console.error('Failed to fetch users:', error)
      setError('Failed to load users. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleActive = async (userId: string) => {
    try {
      await api.patch(`/admin/users/${userId}/toggle-active`)
      fetchUsers()
    } catch (error) {
      setError('Failed to toggle user status')
    }
  }

  const handleDeleteUser = async (userId: string) => {
    if (!window.confirm('Are you sure you want to delete this user?')) {
      return
    }

    try {
      await api.delete(`/admin/users/${userId}`)
      fetchUsers()
    } catch (error) {
      setError('Failed to delete user')
    }
  }

  const handleApproveUser = async (userId: string) => {
    try {
      await api.patch(`/admin/users/${userId}/approve`)
      fetchUsers()
    } catch (error) {
      setError('Failed to approve user')
    }
  }

  const handleRejectUser = async (userId: string) => {
    const reason = window.prompt('Please provide a reason for rejection:')
    if (!reason) return

    try {
      await api.patch(`/admin/users/${userId}/reject`, { reason })
      fetchUsers()
    } catch (error) {
      setError('Failed to reject user')
    }
  }

  const handleSaveUser = async (e: React.MouseEvent) => {
    e.preventDefault()
    console.log('Save user clicked, selectedUser:', selectedUser, 'formData:', formData)
    
    try {
      if (selectedUser) {
        // Update existing user
        console.log('Updating user:', selectedUser.id, formData)
        console.log('API base URL:', api.defaults.baseURL)
        console.log('Full URL:', `${api.defaults.baseURL}/admin/users/${selectedUser.id}`)
        
        const response = await api.patch(`/admin/users/${selectedUser.id}`, formData)
        console.log('Update response:', response.data)
      } else {
        // Create new user
        console.log('Creating user:', formData)
        
        // Validate password for new users
        if (!formData.password || formData.password.length < 8) {
          setError('Password must be at least 8 characters long')
          return
        }
        
        const response = await api.post(`/admin/users`, formData)
        console.log('Create response:', response.data)
      }
      
      setOpenDialog(false)
      fetchUsers()
      setError('')
    } catch (error: any) {
      console.error('Save error:', error)
      setError(error.response?.data?.detail || 'Failed to save user')
    }
  }

  const handleOpenDialog = (user: User | null) => {
    setSelectedUser(user)
    if (user) {
      setFormData({
        email: user.email,
        name: user.full_name,
        password: '',  // Don't show existing password
        is_admin: user.is_admin,
      })
    } else {
      setFormData({
        email: '',
        name: '',
        password: '',
        is_admin: false,
      })
    }
    setOpenDialog(true)
  }

  // Search is handled server-side now
  const filteredUsers = users

  const columns: GridColDef[] = [
    {
      field: 'full_name',
      headerName: 'Name',
      flex: 1,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Typography variant="body2">{params.row.full_name}</Typography>
          <Typography variant="caption" color="text.secondary">
            {params.row.email}
          </Typography>
          {params.row.mfa_enabled && (
            <Chip label="MFA" size="small" color="success" sx={{ mt: 0.5 }} />
          )}
        </Box>
      ),
    },
    {
      field: 'is_active',
      headerName: 'Status',
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          icon={params.row.is_active ? <ActiveIcon /> : <BlockIcon />}
          label={params.row.is_active ? 'Active' : 'Inactive'}
          color={params.row.is_active ? 'success' : 'default'}
          size="small"
        />
      ),
    },
    {
      field: 'approval_status',
      headerName: 'Approval',
      width: 120,
      renderCell: (params: GridRenderCellParams) => {
        const getApprovalChip = () => {
          switch (params.row.approval_status) {
            case 'approved':
              return {
                label: 'Approved',
                color: 'success' as const,
                variant: 'filled' as const
              }
            case 'pending':
              return {
                label: 'Pending',
                color: 'warning' as const,
                variant: 'filled' as const
              }
            case 'rejected':
              return {
                label: 'Rejected',
                color: 'error' as const,
                variant: 'filled' as const
              }
            default:
              return {
                label: 'Unknown',
                color: 'default' as const,
                variant: 'outlined' as const
              }
          }
        }
        const chipProps = getApprovalChip()
        return <Chip {...chipProps} size="small" />
      },
    },
    {
      field: 'is_admin',
      headerName: 'Role',
      width: 100,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.row.is_admin ? 'Admin' : 'User'}
          color={params.row.is_admin ? 'primary' : 'default'}
          size="small"
          variant={params.row.is_admin ? 'filled' : 'outlined'}
        />
      ),
    },
    {
      field: 'stats',
      headerName: 'Stats',
      width: 200,
      renderCell: (params: GridRenderCellParams) => (
        <Box display="flex" gap={0.5}>
          <Chip size="small" label={`${params.row.workspace_count} WS`} />
          <Chip size="small" label={`${params.row.task_count} Tasks`} />
          <Chip size="small" label={`${params.row.device_count} Dev`} />
        </Box>
      ),
    },
    {
      field: 'last_login_at',
      headerName: 'Last Login',
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">
          {params.row.last_login_at
            ? format(new Date(params.row.last_login_at), 'PPp')
            : 'Never'}
        </Typography>
      ),
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">
          {format(new Date(params.row.created_at), 'PP')}
        </Typography>
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 180,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          {params.row.approval_status === 'pending' && (
            <>
              <IconButton
                size="small"
                onClick={() => handleApproveUser(params.row.id)}
                color="success"
                title="Approve user"
              >
                <CheckCircle />
              </IconButton>
              <IconButton
                size="small"
                onClick={() => handleRejectUser(params.row.id)}
                color="error"
                title="Reject user"
              >
                <BlockIcon />
              </IconButton>
            </>
          )}
          <IconButton
            size="small"
            onClick={() => handleToggleActive(params.row.id)}
            color={params.row.is_active ? 'warning' : 'success'}
            title={params.row.is_active ? 'Deactivate user' : 'Activate user'}
          >
            {params.row.is_active ? <BlockIcon /> : <ActiveIcon />}
          </IconButton>
          <IconButton
            size="small"
            onClick={() => handleOpenDialog(params.row)}
            title="Edit user"
          >
            <EditIcon />
          </IconButton>
          <IconButton
            size="small"
            onClick={() => handleDeleteUser(params.row.id)}
            color="error"
          >
            <DeleteIcon />
          </IconButton>
        </Box>
      ),
    },
  ]

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Users</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog(null)}
        >
          Add User
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search users..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </Paper>

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={filteredUsers}
          columns={columns}
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          pageSizeOptions={[10, 25, 50]}
          checkboxSelection
          disableRowSelectionOnClick
          loading={loading}
          rowCount={totalUsers}
          paginationMode="server"
        />
      </Paper>

      {/* User Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedUser ? 'Edit User' : 'Add New User'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Email"
            type="email"
            fullWidth
            variant="outlined"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Name"
            fullWidth
            variant="outlined"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          {!selectedUser && (
            <TextField
              margin="dense"
              label="Password"
              type="password"
              fullWidth
              variant="outlined"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              helperText="Password must be at least 8 characters long"
              required
              sx={{ mb: 2 }}
            />
          )}
          <FormControlLabel
            control={
              <Checkbox 
                checked={formData.is_admin} 
                onChange={(e) => setFormData({ ...formData, is_admin: e.target.checked })}
              />
            }
            label="Admin User"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleSaveUser} variant="contained">
            {selectedUser ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}