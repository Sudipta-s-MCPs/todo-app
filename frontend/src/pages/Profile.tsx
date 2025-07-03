import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Avatar,
  Grid,
  Divider,
  Switch,
  FormControlLabel,
  CircularProgress,
  Alert,
  Stack,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
  Card,
  CardContent,
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  PhotoCamera as PhotoCameraIcon,
  VpnKey as PasswordIcon,
  Visibility,
  VisibilityOff,
  Delete as DeleteIcon,
  Devices as DevicesIcon,
  Computer as ComputerIcon,
  Smartphone as SmartphoneIcon,
} from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { format } from 'date-fns';

import { authService } from '../services/authService';
import { useAuthStore } from '../store/authStore';
import type { UserDevice } from '../types';
import { getDeviceInfo } from '../utils/deviceId';

interface ProfileFormData {
  name: string;
  email: string;
  timezone: string;
  locale: string;
  two_factor_enabled: boolean;
}

interface PasswordFormData {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export default function Profile() {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const user = useAuthStore((state) => state.user);
  const updateUser = useAuthStore((state) => state.updateUser);
  
  const [isEditing, setIsEditing] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [devicesDialogOpen, setDevicesDialogOpen] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [currentDeviceInfo, setCurrentDeviceInfo] = useState<any>(null);
  
  // Get current device info on mount
  useEffect(() => {
    getDeviceInfo().then(info => {
      setCurrentDeviceInfo(info);
    }).catch(err => {
      console.error('Failed to get device info:', err);
    });
  }, []);

  // Profile form
  const {
    control: profileControl,
    handleSubmit: handleProfileSubmit,
    reset: resetProfile,
    formState: { errors: profileErrors, isDirty: isProfileDirty },
  } = useForm<ProfileFormData>({
    defaultValues: {
      name: '',
      email: '',
      timezone: 'UTC',
      locale: 'en',
      two_factor_enabled: false,
    },
  });

  // Password form
  const {
    control: passwordControl,
    handleSubmit: handlePasswordSubmit,
    reset: resetPassword,
    watch: watchPassword,
    formState: { errors: passwordErrors },
  } = useForm<PasswordFormData>({
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  const newPassword = watchPassword('new_password');

  // Set form values when user data is available
  useEffect(() => {
    if (user) {
      resetProfile({
        name: user.name,
        email: user.email,
        timezone: user.timezone,
        locale: user.locale,
        two_factor_enabled: user.two_factor_enabled,
      });
    }
  }, [user, resetProfile]);

  // Queries
  const { data: devices, isLoading: devicesLoading, refetch: refetchDevices } = useQuery<UserDevice[]>({
    queryKey: ['user-devices'],
    queryFn: () => authService.getUserDevices(),
    enabled: devicesDialogOpen,
  });

  // Mutations
  const updateProfileMutation = useMutation({
    mutationFn: (data: Partial<ProfileFormData>) => authService.updateProfile(data),
    onSuccess: (updatedUser) => {
      updateUser(updatedUser);
      queryClient.invalidateQueries({ queryKey: ['current-user'] });
      enqueueSnackbar('Profile updated successfully', { variant: 'success' });
      setIsEditing(false);
    },
    onError: (error: any) => {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to update profile', {
        variant: 'error',
      });
    },
  });

  const updatePasswordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      authService.updatePassword(data.current_password, data.new_password),
    onSuccess: () => {
      enqueueSnackbar('Password updated successfully', { variant: 'success' });
      setPasswordDialogOpen(false);
      resetPassword();
    },
    onError: (error: any) => {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to update password', {
        variant: 'error',
      });
    },
  });

  const revokeDeviceMutation = useMutation({
    mutationFn: (deviceId: string) => authService.revokeDevice(deviceId),
    onSuccess: () => {
      refetchDevices();
      enqueueSnackbar('Device revoked successfully', { variant: 'success' });
    },
    onError: (error: any) => {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to revoke device', {
        variant: 'error',
      });
    },
  });

  const uploadAvatarMutation = useMutation({
    mutationFn: (file: File) => authService.uploadAvatar(file),
    onSuccess: async (data) => {
      // Update user with new avatar URL
      if (user) {
        const updatedUser = { ...user, avatar_url: data.avatar_url };
        updateUser(updatedUser);
        queryClient.invalidateQueries({ queryKey: ['current-user'] });
        enqueueSnackbar('Profile photo updated successfully', { variant: 'success' });
      }
      setAvatarUploading(false);
    },
    onError: (error: any) => {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to upload photo', {
        variant: 'error',
      });
      setAvatarUploading(false);
    },
  });

  // Handlers
  const handleProfileSave = async (data: ProfileFormData) => {
    // Only send fields that can be updated
    const updateData = {
      name: data.name,
      timezone: data.timezone,
      locale: data.locale,
    };
    await updateProfileMutation.mutateAsync(updateData);
  };

  const handlePasswordChange = async (data: PasswordFormData) => {
    if (data.new_password !== data.confirm_password) {
      enqueueSnackbar('Passwords do not match', { variant: 'error' });
      return;
    }
    await updatePasswordMutation.mutateAsync({
      current_password: data.current_password,
      new_password: data.new_password,
    });
  };

  const handleCancelEdit = () => {
    if (user) {
      resetProfile({
        name: user.name,
        email: user.email,
        timezone: user.timezone,
        locale: user.locale,
        two_factor_enabled: user.two_factor_enabled,
      });
    }
    setIsEditing(false);
  };

  const handleRevokeDevice = async (deviceId: string) => {
    if (window.confirm('Are you sure you want to revoke access for this device?')) {
      await revokeDeviceMutation.mutateAsync(deviceId);
    }
  };

  const handleAvatarChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        enqueueSnackbar('Image must be less than 5MB', { variant: 'error' });
        return;
      }
      
      // Validate file type
      if (!file.type.startsWith('image/')) {
        enqueueSnackbar('Please select an image file', { variant: 'error' });
        return;
      }
      
      setAvatarUploading(true);
      await uploadAvatarMutation.mutateAsync(file);
    }
  };

  if (!user) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Profile
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Avatar
              sx={{
                width: 120,
                height: 120,
                mx: 'auto',
                mb: 2,
                fontSize: '3rem',
              }}
              src={user.avatar_url}
            >
              {user.name.charAt(0).toUpperCase()}
            </Avatar>
            <Typography variant="h6" gutterBottom>
              {user.name}
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {user.email}
            </Typography>
            {user.is_admin && (
              <Chip label="Admin" color="primary" size="small" sx={{ mt: 1 }} />
            )}
            <Box mt={2}>
              <input
                accept="image/*"
                id="avatar-upload"
                type="file"
                style={{ display: 'none' }}
                onChange={handleAvatarChange}
                disabled={avatarUploading}
              />
              <label htmlFor="avatar-upload">
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={avatarUploading ? <CircularProgress size={16} /> : <PhotoCameraIcon />}
                  disabled={avatarUploading}
                  component="span"
                >
                  {avatarUploading ? 'Uploading...' : 'Change Photo'}
                </Button>
              </label>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">Personal Information</Typography>
              {!isEditing ? (
                <IconButton onClick={() => setIsEditing(true)}>
                  <EditIcon />
                </IconButton>
              ) : (
                <Box>
                  <IconButton
                    onClick={handleCancelEdit}
                    disabled={updateProfileMutation.isPending}
                  >
                    <CancelIcon />
                  </IconButton>
                  <IconButton
                    onClick={handleProfileSubmit(handleProfileSave)}
                    disabled={updateProfileMutation.isPending || !isProfileDirty}
                    color="primary"
                  >
                    <SaveIcon />
                  </IconButton>
                </Box>
              )}
            </Box>

            <form>
              <Stack spacing={3}>
                <Controller
                  name="name"
                  control={profileControl}
                  rules={{ required: 'Name is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Name"
                      fullWidth
                      disabled={!isEditing}
                      error={!!profileErrors.name}
                      helperText={profileErrors.name?.message}
                    />
                  )}
                />

                <Controller
                  name="email"
                  control={profileControl}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Email"
                      type="email"
                      fullWidth
                      disabled={true}
                      InputProps={{
                        readOnly: true,
                      }}
                    />
                  )}
                />

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Controller
                      name="timezone"
                      control={profileControl}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="Timezone"
                          fullWidth
                          disabled={!isEditing}
                          select
                          SelectProps={{ native: true }}
                        >
                          <option value="UTC">UTC</option>
                          <option value="America/New_York">Eastern Time</option>
                          <option value="America/Chicago">Central Time</option>
                          <option value="America/Denver">Mountain Time</option>
                          <option value="America/Los_Angeles">Pacific Time</option>
                          <option value="Europe/London">London</option>
                          <option value="Europe/Paris">Paris</option>
                          <option value="Asia/Tokyo">Tokyo</option>
                          <option value="Asia/Shanghai">Shanghai</option>
                          <option value="Asia/Kolkata">India</option>
                        </TextField>
                      )}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Controller
                      name="locale"
                      control={profileControl}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          label="Language"
                          fullWidth
                          disabled={!isEditing}
                          select
                          SelectProps={{ native: true }}
                        >
                          <option value="en">English</option>
                          <option value="es">Spanish</option>
                          <option value="fr">French</option>
                          <option value="de">German</option>
                          <option value="ja">Japanese</option>
                          <option value="zh">Chinese</option>
                        </TextField>
                      )}
                    />
                  </Grid>
                </Grid>

                <Box>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={user?.two_factor_enabled || false}
                        disabled={true}
                      />
                    }
                    label="Two-factor authentication"
                  />
                  {!user?.two_factor_enabled && (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ ml: 4 }}>
                      Two-factor authentication adds an extra layer of security to your account
                    </Typography>
                  )}
                </Box>
              </Stack>
            </form>

            <Divider sx={{ my: 3 }} />

            <Box>
              <Typography variant="h6" gutterBottom>
                Security
              </Typography>
              <Stack spacing={2}>
                {user.auth_provider === 'local' ? (
                  <Button
                    variant="outlined"
                    startIcon={<PasswordIcon />}
                    onClick={() => setPasswordDialogOpen(true)}
                  >
                    Change Password
                  </Button>
                ) : (
                  <Alert severity="info" icon={<PasswordIcon />}>
                    {user.auth_provider === 'ldap' 
                      ? 'Password changes for LDAP accounts must be done through your organization\'s LDAP system.'
                      : 'Password changes are managed by your OAuth provider.'}
                  </Alert>
                )}
                <Button
                  variant="outlined"
                  startIcon={<DevicesIcon />}
                  onClick={() => setDevicesDialogOpen(true)}
                >
                  Manage Devices
                </Button>
              </Stack>
            </Box>

            <Divider sx={{ my: 3 }} />

            <Box>
              <Typography variant="h6" gutterBottom>
                Account Information
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">
                    Member since
                  </Typography>
                  <Typography variant="body1">
                    {format(new Date(user.created_at), 'MMMM d, yyyy')}
                  </Typography>
                </Grid>
                {user.last_active_at && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Last active
                    </Typography>
                    <Typography variant="body1">
                      {format(new Date(user.last_active_at), 'MMMM d, yyyy h:mm a')}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </Box>
            
            {currentDeviceInfo && (
              <>
                <Divider sx={{ my: 3 }} />
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Current Device
                  </Typography>
                  <Card variant="outlined" sx={{ bgcolor: 'action.hover' }}>
                    <CardContent>
                      <Box display="flex" alignItems="center" gap={1} mb={1}>
                        {currentDeviceInfo.deviceType === 'pwa' ? <SmartphoneIcon /> : <ComputerIcon />}
                        <Typography variant="subtitle1">
                          {currentDeviceInfo.deviceName}
                        </Typography>
                        <Chip label="This Device" size="small" color="primary" />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        Device ID: {currentDeviceInfo.deviceId}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Type: {currentDeviceInfo.deviceType === 'pwa' ? 'Installed App (PWA)' : 'Web Browser'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        First seen: {format(new Date(currentDeviceInfo.createdAt), 'PPp')}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>
              </>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Change Password Dialog */}
      <Dialog 
        open={passwordDialogOpen} 
        onClose={() => {
          setPasswordDialogOpen(false);
          resetPassword();
          setShowCurrentPassword(false);
          setShowNewPassword(false);
          setShowConfirmPassword(false);
        }} 
        maxWidth="sm" 
        fullWidth
      >
        <form onSubmit={handlePasswordSubmit(handlePasswordChange)}>
          <DialogTitle>Change Password</DialogTitle>
          <DialogContent dividers>
            <Stack spacing={3}>
              <Controller
                name="current_password"
                control={passwordControl}
                rules={{ required: 'Current password is required' }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Current Password"
                    type={showCurrentPassword ? 'text' : 'password'}
                    fullWidth
                    error={!!passwordErrors.current_password}
                    helperText={passwordErrors.current_password?.message}
                    InputProps={{
                      endAdornment: (
                        <IconButton
                          onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                          edge="end"
                        >
                          {showCurrentPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      ),
                    }}
                  />
                )}
              />

              <Controller
                name="new_password"
                control={passwordControl}
                rules={{
                  required: 'New password is required',
                  minLength: {
                    value: 8,
                    message: 'Password must be at least 8 characters',
                  },
                }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="New Password"
                    type={showNewPassword ? 'text' : 'password'}
                    fullWidth
                    error={!!passwordErrors.new_password}
                    helperText={passwordErrors.new_password?.message}
                    InputProps={{
                      endAdornment: (
                        <IconButton
                          onClick={() => setShowNewPassword(!showNewPassword)}
                          edge="end"
                        >
                          {showNewPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      ),
                    }}
                  />
                )}
              />

              <Controller
                name="confirm_password"
                control={passwordControl}
                rules={{
                  required: 'Please confirm your password',
                  validate: (value) =>
                    value === newPassword || 'Passwords do not match',
                }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Confirm New Password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    fullWidth
                    error={!!passwordErrors.confirm_password}
                    helperText={passwordErrors.confirm_password?.message}
                    InputProps={{
                      endAdornment: (
                        <IconButton
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          edge="end"
                        >
                          {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      ),
                    }}
                  />
                )}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => {
              setPasswordDialogOpen(false);
              resetPassword();
              setShowCurrentPassword(false);
              setShowNewPassword(false);
              setShowConfirmPassword(false);
            }}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={updatePasswordMutation.isPending}
            >
              {updatePasswordMutation.isPending ? 'Updating...' : 'Update Password'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Manage Devices Dialog */}
      <Dialog open={devicesDialogOpen} onClose={() => setDevicesDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Manage Devices</DialogTitle>
        <DialogContent dividers>
          {devicesLoading ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : devices && devices.length > 0 ? (
            <List>
              {devices.map((device) => (
                <ListItem key={device.id} divider>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <DevicesIcon fontSize="small" />
                        {device.device_name || 'Unknown Device'}
                        {device.is_current && (
                          <Chip label="Current" size="small" color="primary" />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2">
                          {device.device_type} • {device.device_identifier}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Last active: {format(new Date(device.last_used_at), 'PPp')}
                        </Typography>
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    {!device.is_current && (
                      <IconButton
                        edge="end"
                        onClick={() => handleRevokeDevice(device.id)}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    )}
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          ) : (
            <Alert severity="info">No devices found</Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDevicesDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}