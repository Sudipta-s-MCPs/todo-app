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
  Tooltip,
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
  Settings as ConfigIcon,
} from '@mui/icons-material'
import { format } from 'date-fns'
import { api } from '../services/api'
import McpRegistrationWizard from '../components/McpRegistrationWizard'

interface MCPAgent {
  id: string
  agent_identifier: string
  capabilities: string[]
  is_active: boolean
  last_heartbeat: string | null
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
  const [openWizard, setOpenWizard] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState<MCPAgent | null>(null)
  const [error, setError] = useState('')
  const [totalAgents, setTotalAgents] = useState(0)
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  })
  const [agentConfig, setAgentConfig] = useState<any>(null)
  const [configLoading, setConfigLoading] = useState(false)

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

  const fetchAgentConfig = async (agentId: string) => {
    setConfigLoading(true)
    try {
      const response = await api.get(`/admin/mcp/agents/${agentId}/config`)
      setAgentConfig(response.data.configurations)
    } catch (error) {
      console.error('Failed to fetch agent config:', error)
      setError('Failed to load agent configuration')
    } finally {
      setConfigLoading(false)
    }
  }

  const handleViewConfig = async (agent: MCPAgent) => {
    setSelectedAgent(agent)
    await fetchAgentConfig(agent.id)
    setOpenDialog(true)
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
      (agent.agent_identifier?.toLowerCase() || '').includes(searchQuery.toLowerCase()) ||
      (agent.user?.email?.toLowerCase() || '').includes(searchQuery.toLowerCase()) ||
      (agent.user?.full_name?.toLowerCase() || '').includes(searchQuery.toLowerCase())
  )

  const columns: GridColDef[] = [
    {
      field: 'agent_identifier',
      headerName: 'Agent',
      width: 300,
      renderCell: (params: GridRenderCellParams) => (
        <Box display="flex" alignItems="center">
          <MemoryIcon sx={{ mr: 1, color: 'text.secondary' }} />
          <Box>
            <Typography variant="body2" fontFamily="monospace">
              {params.row.agent_identifier}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              MCP Agent
            </Typography>
          </Box>
        </Box>
      ),
    },
    {
      field: 'description',
      headerName: 'Description',
      flex: 1,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Typography variant="body2">
            MCP Agent for task management
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {params.row.capabilities?.length || 0} capabilities
          </Typography>
        </Box>
      ),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 150,
      renderCell: (params: GridRenderCellParams) => {
        const online = isAgentOnline(params.row.last_heartbeat)
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
      field: 'last_heartbeat',
      headerName: 'Last Active',
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Box display="flex" alignItems="center">
          <AccessTimeIcon sx={{ mr: 0.5, fontSize: 16, color: 'text.secondary' }} />
          <Typography variant="body2">
            {params.row.last_heartbeat
              ? format(new Date(params.row.last_heartbeat), 'PPp')
              : 'Never'}
          </Typography>
        </Box>
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 120,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <Box>
          <Tooltip title="View Configuration">
            <IconButton
              size="small"
              onClick={() => handleViewConfig(params.row)}
            >
              <ConfigIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete Agent">
            <IconButton
              size="small"
              onClick={() => handleDeleteAgent(params.row.id)}
              color="error"
            >
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Box>
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
          onClick={() => setOpenWizard(true)}
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
        />
      </Paper>

      {/* Agent Configuration Dialog */}
      <Dialog open={openDialog} onClose={() => {
        setOpenDialog(false)
        setAgentConfig(null)
      }} maxWidth="md" fullWidth>
        <DialogTitle>
          MCP Agent Configuration
        </DialogTitle>
        <DialogContent>
          {selectedAgent && (
            <Box>
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Agent Details
                </Typography>
                <Typography variant="body2">
                  <strong>Identifier:</strong> {selectedAgent.agent_identifier}
                </Typography>
                <Typography variant="body2">
                  <strong>Owner:</strong> {selectedAgent.user.full_name} ({selectedAgent.user.email})
                </Typography>
                <Typography variant="body2">
                  <strong>Created:</strong> {format(new Date(selectedAgent.created_at), 'PPp')}
                </Typography>
              </Box>

              {configLoading ? (
                <Typography>Loading configuration...</Typography>
              ) : agentConfig ? (
                <Box>
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Use the configuration below in your MCP client. The API key was provided during registration and cannot be retrieved again.
                  </Alert>
                  {agentConfig.claude_code && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Claude Code Configuration (.env)
                      </Typography>
                      <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
                        <pre style={{ margin: 0, overflow: 'auto', fontSize: '0.875rem' }}>
                          {agentConfig.claude_code.content}
                        </pre>
                      </Paper>
                    </Box>
                  )}
                  {agentConfig.claude_desktop && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Claude Desktop Configuration (JSON)
                      </Typography>
                      <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
                        <pre style={{ margin: 0, overflow: 'auto', fontSize: '0.875rem' }}>
                          {JSON.stringify(agentConfig.claude_desktop.content, null, 2)}
                        </pre>
                      </Paper>
                    </Box>
                  )}
                </Box>
              ) : (
                <Alert severity="warning">
                  Failed to load configuration. Please try again.
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setOpenDialog(false)
            setAgentConfig(null)
          }}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Registration Wizard */}
      <McpRegistrationWizard
        open={openWizard}
        onClose={() => setOpenWizard(false)}
        onSuccess={() => {
          setOpenWizard(false)
          fetchAgents()
        }}
      />
    </Box>
  )
}