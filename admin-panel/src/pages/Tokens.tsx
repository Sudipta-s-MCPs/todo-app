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
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Tooltip,
} from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams, GridPaginationModel } from '@mui/x-data-grid'
import {
  Add as AddIcon,
  Search as SearchIcon,
  Delete as DeleteIcon,
  Key as KeyIcon,
  ContentCopy as CopyIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material'
import { format, formatDistanceToNow } from 'date-fns'
import { api } from '../services/api'

interface APIKey {
  id: string
  name: string
  key_preview: string
  full_key?: string
  scopes: string[]
  is_active: boolean
  last_used_at: string | null
  expires_at: string | null
  created_at: string
  user: {
    id: string
    email: string
    full_name: string
  }
}

const AVAILABLE_PERMISSIONS = [
  { value: 'tasks:read', label: 'Read Tasks' },
  { value: 'tasks:write', label: 'Write Tasks' },
  { value: 'workspaces:read', label: 'Read Workspaces' },
  { value: 'workspaces:write', label: 'Write Workspaces' },
  { value: 'users:read', label: 'Read Users' },
  { value: 'users:write', label: 'Write Users' },
  { value: 'admin:read', label: 'Admin Read' },
  { value: 'admin:write', label: 'Admin Write' },
]

export default function Tokens() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [openDialog, setOpenDialog] = useState(false)
  const [newKeyDialog, setNewKeyDialog] = useState(false)
  const [newKey, setNewKey] = useState<string>('')
  const [showKey, setShowKey] = useState(false)
  const [error, setError] = useState('')
  const [totalKeys, setTotalKeys] = useState(0)
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  })

  // Form state for new API key
  const [keyForm, setKeyForm] = useState({
    name: '',
    expires_days: 90,
    permissions: [] as string[],
  })

  useEffect(() => {
    fetchAPIKeys()
  }, [paginationModel])

  const fetchAPIKeys = async () => {
    try {
      setLoading(true)
      const response = await api.get('/admin/api-keys', {
        params: {
          skip: paginationModel.page * paginationModel.pageSize,
          limit: paginationModel.pageSize,
        }
      })
      setApiKeys(response.data.keys)
      setTotalKeys(response.data.total)
    } catch (error) {
      console.error('Failed to fetch API keys:', error)
      setError('Failed to load API keys. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateKey = async () => {
    try {
      const response = await api.post('/auth/api-keys', {
        name: keyForm.name,
        permissions: keyForm.permissions,
        expires_days: keyForm.expires_days > 0 ? keyForm.expires_days : null,
      })
      
      setNewKey(response.data.key)
      setNewKeyDialog(true)
      setOpenDialog(false)
      fetchAPIKeys()
      
      // Reset form
      setKeyForm({
        name: '',
        expires_days: 90,
        permissions: [],
      })
    } catch (error) {
      setError('Failed to create API key')
    }
  }

  const handleDeleteKey = async (keyId: string) => {
    if (!window.confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
      return
    }

    try {
      await api.delete(`/auth/api-keys/${keyId}`)
      fetchAPIKeys()
    } catch (error) {
      setError('Failed to delete API key')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    // You could add a toast notification here
  }

  const isExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false
    return new Date(expiresAt) < new Date()
  }

  const filteredKeys = apiKeys.filter(
    (key) =>
      key.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      key.user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      key.key_preview.includes(searchQuery)
  )

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
      flex: 1,
      renderCell: (params: GridRenderCellParams) => (
        <Box display="flex" alignItems="center">
          <KeyIcon sx={{ mr: 1, color: 'text.secondary' }} />
          <Box>
            <Typography variant="body2">{params.row.name}</Typography>
            <Typography variant="caption" color="text.secondary">
              {params.row.key_preview}
            </Typography>
          </Box>
        </Box>
      ),
    },
    {
      field: 'user',
      headerName: 'Owner',
      width: 200,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Typography variant="body2">{params.row.user.full_name}</Typography>
          <Typography variant="caption" color="text.secondary">
            {params.row.user.email}
          </Typography>
        </Box>
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params: GridRenderCellParams) => {
        const expired = isExpired(params.row.expires_at)
        const active = params.row.is_active && !expired
        
        return (
          <Chip
            label={expired ? 'Expired' : active ? 'Active' : 'Inactive'}
            color={expired ? 'error' : active ? 'success' : 'default'}
            size="small"
          />
        )
      },
    },
    {
      field: 'scopes',
      headerName: 'Scopes',
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">
          {params.row.scopes.length} scopes
        </Typography>
      ),
    },
    {
      field: 'last_used_at',
      headerName: 'Last Used',
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">
          {params.row.last_used_at
            ? formatDistanceToNow(new Date(params.row.last_used_at), { addSuffix: true })
            : 'Never'}
        </Typography>
      ),
    },
    {
      field: 'expires_at',
      headerName: 'Expires',
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" color={isExpired(params.row.expires_at) ? 'error' : 'text.primary'}>
          {params.row.expires_at
            ? format(new Date(params.row.expires_at), 'PP')
            : 'Never'}
        </Typography>
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 100,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Tooltip title="Copy API Key">
            <IconButton
              size="small"
              onClick={() => copyToClipboard(params.row.key_preview)}
            >
              <CopyIcon />
            </IconButton>
          </Tooltip>
          <IconButton
            size="small"
            onClick={() => handleDeleteKey(params.row.id)}
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
        <Typography variant="h4">API Tokens</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpenDialog(true)}
        >
          Create Token
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
          placeholder="Search API keys..."
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
          rows={filteredKeys}
          columns={columns}
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          pageSizeOptions={[10, 25, 50]}
          disableRowSelectionOnClick
          loading={loading}
          rowCount={totalKeys}
          paginationMode="server"
        />
      </Paper>

      {/* Create API Key Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New API Key</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Key Name"
            fullWidth
            variant="outlined"
            value={keyForm.name}
            onChange={(e) => setKeyForm({ ...keyForm, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Expiration</InputLabel>
            <Select
              value={keyForm.expires_days}
              onChange={(e) => setKeyForm({ ...keyForm, expires_days: e.target.value as number })}
              label="Expiration"
            >
              <MenuItem value={0}>Never</MenuItem>
              <MenuItem value={7}>7 days</MenuItem>
              <MenuItem value={30}>30 days</MenuItem>
              <MenuItem value={90}>90 days</MenuItem>
              <MenuItem value={365}>1 year</MenuItem>
            </Select>
          </FormControl>

          <Typography variant="subtitle2" gutterBottom>
            Permissions:
          </Typography>
          <FormGroup>
            {AVAILABLE_PERMISSIONS.map((perm) => (
              <FormControlLabel
                key={perm.value}
                control={
                  <Checkbox
                    checked={keyForm.permissions.includes(perm.value)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setKeyForm({
                          ...keyForm,
                          permissions: [...keyForm.permissions, perm.value],
                        })
                      } else {
                        setKeyForm({
                          ...keyForm,
                          permissions: keyForm.permissions.filter((p) => p !== perm.value),
                        })
                      }
                    }}
                  />
                }
                label={perm.label}
              />
            ))}
          </FormGroup>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleCreateKey} 
            variant="contained"
            disabled={!keyForm.name || keyForm.permissions.length === 0}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* New Key Display Dialog */}
      <Dialog open={newKeyDialog} onClose={() => setNewKeyDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>API Key Created</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This is the only time you'll see this API key. Make sure to copy it now!
          </Alert>
          <TextField
            fullWidth
            variant="outlined"
            value={showKey ? newKey : '••••••••••••••••••••••••••••••••'}
            InputProps={{
              readOnly: true,
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowKey(!showKey)}>
                    {showKey ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                  <IconButton onClick={() => copyToClipboard(newKey)}>
                    <CopyIcon />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewKeyDialog(false)} variant="contained">
            Done
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}