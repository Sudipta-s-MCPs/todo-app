import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Switch,
  Button,
  Grid,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Chip,
  CircularProgress,
  Snackbar,
  Stack,
  Card,
  CardContent,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  FileDownload as ExportIcon,
  FileUpload as ImportIcon,
  Lock as LockIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import IconButton from '@mui/material/IconButton';
import { api } from '../services/api';

interface Setting {
  id: string;
  key: string;
  value: string | null;
  value_type: 'string' | 'int' | 'float' | 'bool' | 'json';
  category: string;
  display_name: string;
  description: string | null;
  is_sensitive: boolean;
  is_readonly: boolean;
  validation_rules: any;
  created_at: string;
  updated_at: string;
  updated_by: string | null;
}

interface CategorySettings {
  category: string;
  display_name: string;
  settings: Setting[];
}

export default function Settings() {
  const [categories, setCategories] = useState<CategorySettings[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [changedSettings, setChangedSettings] = useState<Record<string, string>>({});
  const [expandedCategories, setExpandedCategories] = useState<string[]>([]);
  const [importDialog, setImportDialog] = useState(false);
  const [changeReason, setChangeReason] = useState('');
  const [showSensitiveFields, setShowSensitiveFields] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await api.get('/settings/categories?include_sensitive=true');
      setCategories(response.data);
      // Expand all categories by default
      setExpandedCategories(response.data.map((cat: CategorySettings) => cat.category));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSettingChange = (key: string, value: string, originalSetting?: Setting) => {
    // Don't track changes for masked sensitive values
    if (originalSetting?.is_sensitive && value === '********') {
      return;
    }
    
    setChangedSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const getSettingValue = (setting: Setting): string => {
    if (changedSettings.hasOwnProperty(setting.key)) {
      return changedSettings[setting.key];
    }
    return setting.value || '';
  };

  const saveSettings = async () => {
    if (Object.keys(changedSettings).length === 0) {
      setError('No changes to save');
      return;
    }

    try {
      setSaving(true);
      
      // Filter out any settings that still have masked values
      const filteredSettings: Record<string, string> = {};
      for (const [key, value] of Object.entries(changedSettings)) {
        if (value !== '********') {
          filteredSettings[key] = value;
        }
      }
      
      if (Object.keys(filteredSettings).length === 0) {
        setError('No valid changes to save');
        return;
      }
      
      await api.post('/settings/bulk', {
        settings: filteredSettings,
        change_reason: changeReason || undefined
      });
      
      setSuccess(`Successfully updated ${Object.keys(filteredSettings).length} settings`);
      setChangedSettings({});
      setChangeReason('');
      
      // Reload settings to get updated values
      await loadSettings();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const exportSettings = async () => {
    try {
      const response = await api.get('/settings/export/json', {
        params: { include_sensitive: false }
      });
      
      // Create download link
      const blob = new Blob([JSON.stringify(response.data, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `settings_backup_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      setSuccess('Settings exported successfully');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to export settings');
    }
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post('/settings/import/json', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setSuccess(response.data.message);
      setImportDialog(false);
      
      // Reload settings
      await loadSettings();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to import settings');
    }
  };

  const toggleSensitiveVisibility = (key: string) => {
    setShowSensitiveFields(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const renderSettingInput = (setting: Setting) => {
    const value = getSettingValue(setting);
    const hasChanged = changedSettings.hasOwnProperty(setting.key);
    const showValue = showSensitiveFields[setting.key] || false;

    if (setting.value_type === 'bool') {
      return (
        <FormControlLabel
          control={
            <Switch
              checked={value === 'true'}
              onChange={(e) => handleSettingChange(setting.key, e.target.checked ? 'true' : 'false', setting)}
              disabled={setting.is_readonly}
              color={hasChanged ? 'warning' : 'primary'}
            />
          }
          label={setting.display_name}
        />
      );
    }

    return (
      <TextField
        fullWidth
        label={setting.display_name}
        value={value}
        onChange={(e) => handleSettingChange(setting.key, e.target.value, setting)}
        disabled={setting.is_readonly}
        type={setting.is_sensitive && !showValue ? 'password' : (setting.value_type === 'int' || setting.value_type === 'float' ? 'number' : 'text')}
        multiline={setting.value_type === 'json' && !setting.is_sensitive}
        rows={setting.value_type === 'json' ? 4 : 1}
        helperText={setting.is_sensitive && value === '********' && !showValue ? 
          'Current value is hidden. Enter a new value to update.' : 
          setting.description}
        placeholder={setting.is_sensitive && value === '********' ? 'Enter new value' : undefined}
        InputProps={{
          endAdornment: (
            <>
              {setting.is_sensitive && (
                <>
                  <IconButton
                    size="small"
                    onClick={() => toggleSensitiveVisibility(setting.key)}
                    edge="end"
                  >
                    <Tooltip title={showValue ? "Hide value" : "Show value"}>
                      {showValue ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </Tooltip>
                  </IconButton>
                  <Tooltip title="Sensitive value">
                    <LockIcon color="action" fontSize="small" sx={{ ml: 1 }} />
                  </Tooltip>
                </>
              )}
              {setting.is_readonly && (
                <Tooltip title="Read-only">
                  <LockIcon color="disabled" fontSize="small" />
                </Tooltip>
              )}
            </>
          )
        }}
        sx={{
          '& .MuiOutlinedInput-root': {
            ...(hasChanged && {
              '& fieldset': {
                borderColor: 'warning.main',
                borderWidth: 2
              }
            })
          }
        }}
      />
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">System Settings</Typography>
        <Stack direction="row" spacing={1}>
          <Button
            startIcon={<RefreshIcon />}
            onClick={loadSettings}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            startIcon={<ExportIcon />}
            onClick={exportSettings}
          >
            Export
          </Button>
          <Button
            startIcon={<ImportIcon />}
            onClick={() => setImportDialog(true)}
          >
            Import
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {Object.keys(changedSettings).length > 0 && (
        <Card sx={{ mb: 3, bgcolor: 'warning.lighter' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Unsaved Changes ({Object.keys(changedSettings).length})
            </Typography>
            <TextField
              fullWidth
              label="Change Reason (Optional)"
              value={changeReason}
              onChange={(e) => setChangeReason(e.target.value)}
              helperText="Provide a reason for these changes for audit purposes"
              sx={{ mb: 2 }}
            />
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={saveSettings}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save All Changes'}
            </Button>
          </CardContent>
        </Card>
      )}

      <Grid container spacing={3}>
        {categories.map((category) => (
          <Grid item xs={12} key={category.category}>
            <Accordion
              expanded={expandedCategories.includes(category.category)}
              onChange={(_, expanded) => {
                setExpandedCategories(prev =>
                  expanded
                    ? [...prev, category.category]
                    : prev.filter(c => c !== category.category)
                );
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">
                  {category.display_name}
                  <Chip
                    label={category.settings.length}
                    size="small"
                    sx={{ ml: 2 }}
                  />
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={3}>
                  {category.settings.map((setting) => (
                    <Grid item xs={12} md={6} key={setting.key}>
                      {renderSettingInput(setting)}
                    </Grid>
                  ))}
                </Grid>
              </AccordionDetails>
            </Accordion>
          </Grid>
        ))}
      </Grid>

      {/* Import Dialog */}
      <Dialog open={importDialog} onClose={() => setImportDialog(false)}>
        <DialogTitle>Import Settings</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Upload a JSON file containing exported settings. This will overwrite
            existing values for the imported settings.
          </Typography>
          <Box mt={2}>
            <input
              type="file"
              accept=".json"
              onChange={handleImport}
              style={{ display: 'none' }}
              id="import-file"
            />
            <label htmlFor="import-file">
              <Button
                variant="contained"
                component="span"
                startIcon={<ImportIcon />}
              >
                Choose File
              </Button>
            </label>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportDialog(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar
        open={!!success}
        autoHideDuration={6000}
        onClose={() => setSuccess(null)}
      >
        <Alert onClose={() => setSuccess(null)} severity="success">
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
}