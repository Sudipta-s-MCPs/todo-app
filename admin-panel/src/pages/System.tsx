import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  LinearProgress,
  Button,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableRow,
  CircularProgress,
} from '@mui/material'
import {
  Storage as StorageIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts'
import { api } from '../services/api'

interface SystemInfo {
  system: {
    platform: string
    platform_release: string
    platform_version: string
    architecture: string
    processor: string
    python_version: string
    hostname: string
  }
  cpu: {
    physical_cores: number
    logical_cores: number
    cpu_usage_percent: number
    cpu_freq?: {
      current: number
      min: number
      max: number
    }
  }
  memory: {
    total: number
    available: number
    used: number
    percent: number
    free: number
  }
  disk: {
    total: number
    used: number
    free: number
    percent: number
  }
  database: {
    version?: string
    size?: number
    connections?: {
      total_connections: number
      active_connections: number
      idle_connections: number
    }
    error?: string
  }
  application: {
    name: string
    version: string
    environment: string
    uptime: string
    api_prefix: string
    debug_mode: boolean
  }
}

interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  checks: {
    database?: {
      status: 'healthy' | 'warning' | 'unhealthy'
      message: string
    }
    redis?: {
      status: 'healthy' | 'warning' | 'unhealthy'
      message: string
    }
    memory?: {
      status: 'healthy' | 'warning' | 'unhealthy'
      message: string
    }
    disk?: {
      status: 'healthy' | 'warning' | 'unhealthy'
      message: string
    }
    cpu?: {
      status: 'healthy' | 'warning' | 'unhealthy'
      message: string
    }
  }
}

interface SystemConfig {
  project_name: string
  version: string
  api_prefix: string
  cors_origins: string[]
  access_token_expire_minutes: number
  refresh_token_expire_days: number
  mcp_token_expire_hours: number
  features: {
    oauth_enabled: boolean
    mfa_enabled: boolean
    api_keys_enabled: boolean
    websockets_enabled: boolean
    ldap_enabled: boolean
  }
  limits: {
    max_workspaces_per_user: number
    max_lists_per_workspace: number
    max_tasks_per_list: number
    max_api_keys_per_user: number
    max_devices_per_user: number
  }
}

interface ServiceStatus {
  enabled: boolean
  connected: boolean
  message: string
  endpoint: string | null
}

interface ServicesStatus {
  timestamp: string
  services: {
    ldap?: ServiceStatus
    minio?: ServiceStatus
    qdrant?: ServiceStatus
    groq?: ServiceStatus
  }
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042']

export default function System() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null)
  const [servicesStatus, setServicesStatus] = useState<ServicesStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSystemData()
    // Refresh system info every 30 seconds
    const interval = setInterval(fetchSystemData, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchSystemData = async () => {
    try {
      setError(null)
      const [infoRes, healthRes, configRes, servicesRes] = await Promise.all([
        api.get('/system/info'),
        api.get('/system/health'),
        api.get('/system/config'),
        api.get('/system/services-status'),
      ])
      
      setSystemInfo(infoRes.data)
      setSystemHealth(healthRes.data)
      setSystemConfig(configRes.data)
      setServicesStatus(servicesRes.data)
    } catch (error) {
      console.error('Failed to fetch system data:', error)
      setError('Failed to load system information')
    } finally {
      setLoading(false)
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatUptime = (isoDate: string) => {
    const start = new Date(isoDate)
    const now = new Date()
    const diff = now.getTime() - start.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    return `${days}d ${hours}h`
  }

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'healthy':
        return <CheckIcon color="success" />
      case 'warning':
      case 'degraded':
        return <WarningIcon color="warning" />
      case 'unhealthy':
      case 'error':
        return <ErrorIcon color="error" />
      default:
        return null
    }
  }

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'healthy':
        return 'success.main'
      case 'warning':
      case 'degraded':
        return 'warning.main'
      case 'unhealthy':
      case 'error':
        return 'error.main'
      default:
        return 'text.secondary'
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={fetchSystemData}>
            Retry
          </Button>
        }>
          {error}
        </Alert>
      </Box>
    )
  }

  if (!systemInfo || !systemHealth || !systemConfig) {
    return <Typography>No data available</Typography>
  }

  const memoryData = [
    { name: 'Used', value: systemInfo.memory.used },
    { name: 'Free', value: systemInfo.memory.free },
  ]

  const diskData = [
    { name: 'Used', value: systemInfo.disk.used },
    { name: 'Free', value: systemInfo.disk.free },
  ]

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">System Information</Typography>
        <Button
          startIcon={<RefreshIcon />}
          variant="outlined"
          onClick={fetchSystemData}
        >
          Refresh
        </Button>
      </Box>

      {/* Health Status */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" alignItems="center" mb={2}>
          {getStatusIcon(systemHealth.status)}
          <Typography variant="h6" sx={{ ml: 1 }}>
            System Health: {systemHealth.status.toUpperCase()}
          </Typography>
        </Box>
        <Grid container spacing={2}>
          {Object.entries(systemHealth.checks).map(([key, check]) => (
            <Grid item xs={12} sm={6} md={2.4} key={key}>
              <Box display="flex" alignItems="center">
                {getStatusIcon(check.status)}
                <Box ml={1}>
                  <Typography variant="body2" fontWeight="medium">
                    {key.charAt(0).toUpperCase() + key.slice(1)}
                  </Typography>
                  <Typography variant="caption" color={getStatusColor(check.status)}>
                    {check.status}
                  </Typography>
                </Box>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* External Services Status */}
      {servicesStatus && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            External Services
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(servicesStatus.services).map(([serviceName, service]) => (
              <Grid item xs={12} sm={6} md={3} key={serviceName}>
                <Card variant="outlined">
                  <CardContent sx={{ p: 2 }}>
                    <Box display="flex" alignItems="center" mb={1}>
                      {service.connected ? (
                        <CheckIcon color="success" />
                      ) : service.enabled ? (
                        <ErrorIcon color="error" />
                      ) : (
                        <WarningIcon color="warning" />
                      )}
                      <Typography variant="subtitle1" sx={{ ml: 1, fontWeight: 'medium' }}>
                        {serviceName.toUpperCase()}
                      </Typography>
                    </Box>
                    <Typography 
                      variant="caption" 
                      color={service.connected ? 'success.main' : service.enabled ? 'error.main' : 'text.secondary'}
                      display="block"
                    >
                      {service.message}
                    </Typography>
                    {service.endpoint && (
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                        {service.endpoint}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {/* System Overview */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Details
              </Typography>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell>Platform</TableCell>
                    <TableCell>{systemInfo.system.platform} {systemInfo.system.platform_release}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Architecture</TableCell>
                    <TableCell>{systemInfo.system.architecture}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Hostname</TableCell>
                    <TableCell>{systemInfo.system.hostname}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Python Version</TableCell>
                    <TableCell>{systemInfo.system.python_version}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>App Version</TableCell>
                    <TableCell>{systemInfo.application.version}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Environment</TableCell>
                    <TableCell>
                      <Chip 
                        label={systemInfo.application.environment} 
                        size="small" 
                        color={systemInfo.application.environment === 'production' ? 'success' : 'warning'}
                      />
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Uptime</TableCell>
                    <TableCell>{formatUptime(systemInfo.application.uptime)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Database Information
              </Typography>
              <Table size="small">
                <TableBody>
                  {systemInfo.database.error ? (
                    <TableRow>
                      <TableCell colSpan={2}>
                        <Alert severity="error">{systemInfo.database.error}</Alert>
                      </TableCell>
                    </TableRow>
                  ) : (
                    <>
                      <TableRow>
                        <TableCell>Version</TableCell>
                        <TableCell>{systemInfo.database.version?.split('\n')[0]}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Size</TableCell>
                        <TableCell>{formatBytes(systemInfo.database.size || 0)}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Total Connections</TableCell>
                        <TableCell>{systemInfo.database.connections?.total_connections || 0}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Active Connections</TableCell>
                        <TableCell>{systemInfo.database.connections?.active_connections || 0}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Idle Connections</TableCell>
                        <TableCell>{systemInfo.database.connections?.idle_connections || 0}</TableCell>
                      </TableRow>
                    </>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Resource Usage */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <SpeedIcon sx={{ mr: 1 }} />
                <Typography variant="h6">CPU Usage</Typography>
              </Box>
              <Box textAlign="center" mb={2}>
                <Typography variant="h3" color="primary">
                  {systemInfo.cpu.cpu_usage_percent}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {systemInfo.cpu.physical_cores} cores ({systemInfo.cpu.logical_cores} logical)
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={systemInfo.cpu.cpu_usage_percent} 
                sx={{ height: 10, borderRadius: 5 }}
                color={systemInfo.cpu.cpu_usage_percent > 80 ? 'error' : 'primary'}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <MemoryIcon sx={{ mr: 1 }} />
                <Typography variant="h6">Memory Usage</Typography>
              </Box>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie
                    data={memoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={30}
                    outerRadius={40}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {memoryData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip formatter={(value: number) => formatBytes(value)} />
                </PieChart>
              </ResponsiveContainer>
              <Box textAlign="center">
                <Typography variant="body2">
                  {formatBytes(systemInfo.memory.used)} / {formatBytes(systemInfo.memory.total)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {systemInfo.memory.percent}% used
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <StorageIcon sx={{ mr: 1 }} />
                <Typography variant="h6">Disk Usage</Typography>
              </Box>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie
                    data={diskData}
                    cx="50%"
                    cy="50%"
                    innerRadius={30}
                    outerRadius={40}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {diskData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip formatter={(value: number) => formatBytes(value)} />
                </PieChart>
              </ResponsiveContainer>
              <Box textAlign="center">
                <Typography variant="body2">
                  {formatBytes(systemInfo.disk.used)} / {formatBytes(systemInfo.disk.total)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {systemInfo.disk.percent}% used
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* System Configuration */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Features
              </Typography>
              <Grid container spacing={2}>
                {Object.entries(systemConfig.features).map(([feature, enabled]) => (
                  <Grid item xs={6} key={feature}>
                    <Box display="flex" alignItems="center">
                      {enabled ? (
                        <CheckIcon color="success" sx={{ mr: 1 }} />
                      ) : (
                        <ErrorIcon color="error" sx={{ mr: 1 }} />
                      )}
                      <Typography variant="body2">
                        {feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Limits
              </Typography>
              <Table size="small">
                <TableBody>
                  {Object.entries(systemConfig.limits).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</TableCell>
                      <TableCell align="right">{value}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}