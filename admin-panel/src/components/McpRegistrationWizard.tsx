import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stepper,
  Step,
  StepLabel,
  Button,
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Typography,
  Alert,
  Autocomplete,
  FormControlLabel,
  Checkbox,
  IconButton,
  Paper,
  Tab,
  Tabs,
  Tooltip,
} from '@mui/material'
import {
  ContentCopy as CopyIcon,
  CheckCircle as CheckIcon,
  Download as DownloadIcon,
} from '@mui/icons-material'
import { api } from '../services/api'

interface User {
  id: string
  email: string
  full_name: string
}

interface McpRegistrationWizardProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

const steps = ['Select User', 'Agent Details', 'Capabilities', 'Configuration']

const defaultCapabilities = [
  { value: 'task_management', label: 'Task Management', default: true },
  { value: 'list_management', label: 'List Management', default: true },
  { value: 'search', label: 'Search', default: true },
  { value: 'duplicate_detection', label: 'Duplicate Detection', default: true },
  { value: 'smart_todo_manager', label: 'Smart Todo Manager (AI)', default: true },
]

const clientTypes = [
  { value: 'claude_code', label: 'Claude Code' },
  { value: 'claude_desktop', label: 'Claude Desktop' },
  { value: 'vscode', label: 'VS Code' },
  { value: 'generic', label: 'Generic/Other' },
]

export default function McpRegistrationWizard({
  open,
  onClose,
  onSuccess,
}: McpRegistrationWizardProps) {
  const [activeStep, setActiveStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [users, setUsers] = useState<User[]>([])
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [agentName, setAgentName] = useState('')
  const [description, setDescription] = useState('')
  const [clientType, setClientType] = useState('claude_code')
  const [selectedCapabilities, setSelectedCapabilities] = useState<string[]>(
    defaultCapabilities.filter(c => c.default).map(c => c.value)
  )
  const [configurations, setConfigurations] = useState<any>(null)
  const [copiedConfig, setCopiedConfig] = useState<string | null>(null)
  const [selectedTab, setSelectedTab] = useState(0)

  useEffect(() => {
    if (open) {
      fetchUsers()
      // Reset state when opening
      setActiveStep(0)
      setSelectedUser(null)
      setAgentName('')
      setDescription('')
      setClientType('claude_code')
      setSelectedCapabilities(defaultCapabilities.filter(c => c.default).map(c => c.value))
      setConfigurations(null)
      setError('')
    }
  }, [open])

  const fetchUsers = async () => {
    try {
      const response = await api.get('/admin/users?limit=100')
      setUsers(response.data.users)
    } catch (error) {
      console.error('Failed to fetch users:', error)
      setError('Failed to load users')
    }
  }

  const handleNext = async () => {
    if (activeStep === steps.length - 1) {
      // Final step - close wizard
      onSuccess()
      onClose()
      return
    }

    if (activeStep === 2) {
      // After capabilities, register the agent
      await registerAgent()
    } else {
      setActiveStep((prevStep) => prevStep + 1)
    }
  }

  const handleBack = () => {
    setActiveStep((prevStep) => prevStep - 1)
  }

  const registerAgent = async () => {
    if (!selectedUser) {
      setError('Please select a user')
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await api.post('/admin/mcp/register', {
        user_id: selectedUser.id,
        agent_name: agentName || `${clientType} Agent`,
        description: description || `${getClientLabel(clientType)} on ${selectedUser.full_name}'s device`,
        capabilities: selectedCapabilities,
      })

      setConfigurations(response.data.configurations)
      setActiveStep(3) // Move to configuration step
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to register MCP agent')
    } finally {
      setLoading(false)
    }
  }

  const getClientLabel = (type: string) => {
    return clientTypes.find(c => c.value === type)?.label || type
  }

  const copyToClipboard = async (text: string, configType: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedConfig(configType)
      setTimeout(() => setCopiedConfig(null), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  const downloadConfig = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box sx={{ mt: 2, minHeight: 300 }}>
            <Autocomplete
              options={users}
              getOptionLabel={(option) => `${option.full_name} (${option.email})`}
              value={selectedUser}
              onChange={(_, newValue) => setSelectedUser(newValue)}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Select User"
                  variant="outlined"
                  fullWidth
                  required
                  helperText="Choose the user who will own this MCP agent"
                />
              )}
              sx={{ mb: 3 }}
            />
            {selectedUser && (
              <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                <Typography variant="subtitle2" gutterBottom>
                  Selected User Details
                </Typography>
                <Typography variant="body2">
                  <strong>Name:</strong> {selectedUser.full_name}
                </Typography>
                <Typography variant="body2">
                  <strong>Email:</strong> {selectedUser.email}
                </Typography>
                <Typography variant="body2">
                  <strong>User ID:</strong> {selectedUser.id}
                </Typography>
              </Paper>
            )}
          </Box>
        )

      case 1:
        return (
          <Box sx={{ mt: 2, minHeight: 300 }}>
            <TextField
              label="Agent Name"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              fullWidth
              variant="outlined"
              placeholder="e.g., Claude Code on MacBook"
              helperText="A friendly name for this MCP agent"
              sx={{ mb: 3 }}
            />
            <TextField
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              fullWidth
              variant="outlined"
              multiline
              rows={3}
              placeholder="e.g., Development machine for frontend work"
              helperText="Optional description of where/how this agent will be used"
              sx={{ mb: 3 }}
            />
            <FormControl fullWidth variant="outlined">
              <InputLabel>Client Type</InputLabel>
              <Select
                value={clientType}
                onChange={(e) => setClientType(e.target.value)}
                label="Client Type"
              >
                {clientTypes.map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    {type.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        )

      case 2:
        return (
          <Box sx={{ mt: 2, minHeight: 300 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Select the capabilities this MCP agent should have:
            </Typography>
            {defaultCapabilities.map((capability) => (
              <FormControlLabel
                key={capability.value}
                control={
                  <Checkbox
                    checked={selectedCapabilities.includes(capability.value)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedCapabilities([...selectedCapabilities, capability.value])
                      } else {
                        setSelectedCapabilities(
                          selectedCapabilities.filter((c) => c !== capability.value)
                        )
                      }
                    }}
                  />
                }
                label={capability.label}
                sx={{ display: 'block', mb: 1 }}
              />
            ))}
            <Alert severity="info" sx={{ mt: 2 }}>
              The Smart Todo Manager capability enables AI-powered conversational task management.
            </Alert>
          </Box>
        )

      case 3:
        return (
          <Box sx={{ mt: 2, minHeight: 300 }}>
            {configurations && (
              <>
                <Alert severity="success" sx={{ mb: 3 }}>
                  MCP agent registered successfully! Copy the configuration below and add it to your MCP client.
                </Alert>
                
                <Tabs
                  value={selectedTab}
                  onChange={(_, newValue) => setSelectedTab(newValue)}
                  sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
                >
                  {Object.keys(configurations).map((key) => (
                    <Tab key={key} label={getClientLabel(key)} />
                  ))}
                </Tabs>

                {Object.entries(configurations).map(([key, config]: [string, any], idx) => (
                  <Box
                    key={key}
                    hidden={selectedTab !== idx}
                    sx={{ position: 'relative' }}
                  >
                    {config.format === 'env' ? (
                      <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="subtitle2">.env Configuration</Typography>
                          <Box>
                            <Tooltip title="Copy to clipboard">
                              <IconButton
                                size="small"
                                onClick={() => copyToClipboard(config.content, key)}
                              >
                                {copiedConfig === key ? <CheckIcon /> : <CopyIcon />}
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Download as .env file">
                              <IconButton
                                size="small"
                                onClick={() => downloadConfig(config.content, 'smart-todo-mcp.env')}
                              >
                                <DownloadIcon />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </Box>
                        <pre style={{ margin: 0, overflow: 'auto', fontSize: '0.875rem' }}>
                          {config.content}
                        </pre>
                      </Paper>
                    ) : (
                      <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="subtitle2">JSON Configuration</Typography>
                          <Box>
                            <Tooltip title="Copy to clipboard">
                              <IconButton
                                size="small"
                                onClick={() =>
                                  copyToClipboard(JSON.stringify(config.content, null, 2), key)
                                }
                              >
                                {copiedConfig === key ? <CheckIcon /> : <CopyIcon />}
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Download as JSON file">
                              <IconButton
                                size="small"
                                onClick={() =>
                                  downloadConfig(
                                    JSON.stringify(config.content, null, 2),
                                    `smart-todo-mcp-${key}.json`
                                  )
                                }
                              >
                                <DownloadIcon />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </Box>
                        <pre style={{ margin: 0, overflow: 'auto', fontSize: '0.875rem' }}>
                          {JSON.stringify(config.content, null, 2)}
                        </pre>
                      </Paper>
                    )}
                  </Box>
                ))}

                <Alert severity="warning" sx={{ mt: 3 }}>
                  <strong>Important:</strong> Save the API key now. It cannot be retrieved later for security reasons.
                </Alert>
              </>
            )}
          </Box>
        )

      default:
        return null
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Register MCP Agent</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {renderStepContent(activeStep)}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleBack} disabled={activeStep === 0 || loading}>
          Back
        </Button>
        <Button
          onClick={handleNext}
          variant="contained"
          disabled={
            loading ||
            (activeStep === 0 && !selectedUser) ||
            (activeStep === 1 && !agentName.trim()) ||
            (activeStep === 2 && selectedCapabilities.length === 0)
          }
        >
          {activeStep === steps.length - 1
            ? 'Finish'
            : activeStep === 2
            ? 'Register Agent'
            : 'Next'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}