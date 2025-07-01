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
} from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams, GridPaginationModel } from '@mui/x-data-grid'
import {
  Add as AddIcon,
  Search as SearchIcon,
  Delete as DeleteIcon,
  Memory as MemoryIcon,
  AccessTime as AccessTimeIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
} from '@mui/icons-material'
import { format } from 'date-fns'
import { api } from '../services/api'

interface MCPAgent {
  id: string
  agent_id: string
  client_info: {
    name?: string
    description?: string
    version?: string
  }
  capabilities: string[]
  is_active: boolean
  last_active_at: string | null
  token_expires_at: string | null
  created_at: string
  user: {
    id: string
    email: string
    full_name: string
  }
}

export default function MCPClients() {
  const [agents, setAgents] = useState<MCPAgent[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [openDialog, setOpenDialog] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState<MCPAgent | null>(null)
  const [error, setError] = useState('')
  const [totalAgents, setTotalAgents] = useState(0)
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  })

  useEffect(() => {
    fetchAgents()
    // Set up periodic refresh for active status
    const interval = setInterval(fetchAgents, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [paginationModel])

  const fetchAgents = async () => {
    try {
      setLoading(true)
      const response = await api.get('/admin/mcp/agents', {
        params: {
          skip: paginationModel.page * paginationModel.pageSize,
          limit: paginationModel.pageSize,
        }
      })
      setAgents(response.data.agents)
      setTotalAgents(response.data.total)
    } catch (error) {
      console.error('Failed to fetch MCP agents:', error)
      setError('Failed to load MCP agents. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteAgent = async (agentId: string) => {
    if (!window.confirm('Are you sure you want to delete this MCP agent?')) {
      return
    }

    try {
      await api.delete(`/admin/mcp/agents/${agentId}`)
      fetchAgents()
    } catch (error) {
      setError('Failed to delete MCP agent')
    }
  }

  const isAgentOnline = (lastActiveAt: string | null) => {
    if (!lastActiveAt) return false
    const lastActive = new Date(lastActiveAt)
    const now = new Date()
    const diffMinutes = (now.getTime() - lastActive.getTime()) / (1000 * 60)
    return diffMinutes < 5 // Consider online if active within 5 minutes
  }

  // Search is handled client-side for now
  const filteredAgents = agents.filter(
    (agent) =>
      agent.agent_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.client_info.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.user.email.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const columns: GridColDef[] = [
    {
      field: 'agent_id',
      headerName: 'Agent',
      width: 300,
      renderCell: (params: GridRenderCellParams) => (
        <Box display="flex" alignItems="center">
          <MemoryIcon sx={{ mr: 1, color: 'text.secondary' }} />
          <Box>
            <Typography variant="body2" fontFamily="monospace">
              {params.row.agent_id}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {params.row.client_info?.name || 'Unnamed Agent'}
            </Typography>
          </Box>
        </Box>
      ),
    },
    {
      field: 'client_info',
      headerName: 'Description',
      flex: 1,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Typography variant="body2">
            {params.row.client_info?.description || 'No description'}
          </Typography>
          {params.row.client_info?.version && (
            <Chip label={`v${params.row.client_info.version}`} size="small" sx={{ mt: 0.5 }} />
          )}
        </Box>
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 150,
      renderCell: (params: GridRenderCellParams) => {
        const online = isAgentOnline(params.row.last_active_at)
        const active = params.row.is_active
        return (
          <Box display="flex" gap={0.5}>
            {active ? (
              <Chip
                icon={online ? <ActiveIcon /> : <InactiveIcon />}
                label={online ? 'Online' : 'Offline'}
                color={online ? 'success' : 'warning'}
                size="small"
              />
            ) : (
              <Chip
                label="Inactive"
                color="default"
                size="small"
              />
            )}
          </Box>
        )
      },
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
      field: 'capabilities',
      headerName: 'Capabilities',
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">
          {params.row.capabilities.length} capabilities
        </Typography>
      ),
    },
    {
      field: 'last_active_at',
      headerName: 'Last Active',
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Box display="flex" alignItems="center">
          <AccessTimeIcon sx={{ mr: 0.5, fontSize: 16, color: 'text.secondary' }} />
          <Typography variant="body2">
            {params.row.last_active_at
              ? format(new Date(params.row.last_active_at), 'PPp')
              : 'Never'}
          </Typography>
        </Box>
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 100,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <IconButton
          size="small"
          onClick={() => handleDeleteAgent(params.row.id)}
          color="error"
        >
          <DeleteIcon />
        </IconButton>
      ),
    },
  ]

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">MCP Clients</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            setSelectedAgent(null)
            setOpenDialog(true)
          }}
        >
          Register Agent
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
          placeholder="Search MCP agents..."
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
          rows={filteredAgents}
          columns={columns}
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          pageSizeOptions={[10, 25, 50]}
          disableRowSelectionOnClick
          loading={loading}
          rowCount={totalAgents}
          paginationMode="server"
          onRowClick={(params) => {
            setSelectedAgent(params.row)
            setOpenDialog(true)
          }}
        />
      </Paper>

      {/* Agent Details Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {selectedAgent ? 'MCP Agent Details' : 'Register New MCP Agent'}
        </DialogTitle>
        <DialogContent>
          {selectedAgent ? (
            <Box>
              <TextField
                margin="dense"
                label="Agent ID"
                fullWidth
                variant="outlined"
                value={selectedAgent.agent_id}
                disabled
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                label="Client Name"
                fullWidth
                variant="outlined"
                value={selectedAgent.client_info?.name || 'Unnamed'}
                disabled
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                label="Description"
                fullWidth
                variant="outlined"
                multiline
                rows={2}
                value={selectedAgent.client_info?.description || 'No description'}
                disabled
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                label="Owner"
                fullWidth
                variant="outlined"
                value={`${selectedAgent.user.full_name} (${selectedAgent.user.email})`}
                disabled
                sx={{ mb: 2 }}
              />
              <Typography variant="subtitle2" gutterBottom>
                Capabilities:
              </Typography>
              <Box display="flex" gap={0.5} flexWrap="wrap" mb={2}>
                {selectedAgent.capabilities.map((cap) => (
                  <Chip key={cap} label={cap} size="small" />
                ))}
              </Box>
              <Typography variant="subtitle2" gutterBottom>
                Token Expires:
              </Typography>
              <Typography variant="body2">
                {selectedAgent.token_expires_at
                  ? format(new Date(selectedAgent.token_expires_at), 'PPp')
                  : 'No expiration'}
              </Typography>
            </Box>
          ) : (
            <Alert severity="info">
              To register a new MCP agent, use the MCP setup script or API endpoint with proper authentication.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}