import React, { useState, useEffect } from 'react';
import { Container, Typography, Box, Paper, Button, Grid, TextField, Switch, FormControlLabel, FormGroup, Divider, Alert, CircularProgress, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions } from '@mui/material';
import SkeletonLoader from '../../components/common/SkeletonLoader';
import styled from 'styled-components';

// Styled components for skeleton spacing
const LeftMarginSkeleton = styled(SkeletonLoader)`
  margin-left: 10px;
`;

const BottomMarginSkeleton = styled(SkeletonLoader)`
  margin-bottom: 24px;
`;

// Form field error message styling
const ErrorMessage = styled.div`
  color: ${({ theme }) => theme.colors.error};
  font-size: ${({ theme }) => theme.typography.fontSize.xs};
  margin-top: 4px;
`;

// Dialog confirmation type
interface ConfirmDialogState {
  open: boolean;
  title: string;
  message: string;
  fieldName: string;
  newValue: boolean;
}

// Mock settings data - would come from API in production
const initialSettings = {
  appTitle: 'FormIQ',
  appDescription: 'AI-powered fitness tracking and form analysis',
  maintenanceMode: false,
  allowNewRegistrations: true,
  storageProvider: 's3',
  maxUploadSizeMB: 50,
  rateLimit: 100,
  notificationsEnabled: true,
  emailNotifications: true,
  pushNotifications: true,
  analyticsEnabled: true
};

// Validation rules
interface ValidationErrors {
  appTitle?: string;
  appDescription?: string;
  maxUploadSizeMB?: string;
  rateLimit?: string;
}

export const AdminSettings: React.FC = () => {
  const [settings, setSettings] = useState(initialSettings);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  
  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    open: false,
    title: '',
    message: '',
    fieldName: '',
    newValue: false
  });
  
  // Section loading states for progressive loading effect
  const [sectionLoading, setSectionLoading] = useState({
    general: true,
    storage: true,
    security: true,
    notifications: true
  });

  useEffect(() => {
    // Simulate API fetch for settings with staggered section loading
    const fetchSettings = async () => {
      try {
        // In production, this would be a real API call
        // const response = await api.get('/admin/settings');
        // setSettings(response.data);
        
        // Progressive/staggered loading simulation for better UX
        setTimeout(() => {
          setSectionLoading(prev => ({ ...prev, general: false }));
        }, 800);
        
        setTimeout(() => {
          setSectionLoading(prev => ({ ...prev, storage: false }));
        }, 1200);
        
        setTimeout(() => {
          setSectionLoading(prev => ({ ...prev, security: false }));
        }, 1600);
        
        setTimeout(() => {
          setSectionLoading(prev => ({ ...prev, notifications: false }));
          setLoading(false);
        }, 2000);
        
        // Set the data
        setSettings(initialSettings);
      } catch (err) {
        console.error('Error fetching settings:', err);
        setError('Failed to load settings. Please try again.');
        setLoading(false);
        // Clear all section loading states on error
        setSectionLoading({
          general: false,
          storage: false,
          security: false,
          notifications: false
        });
      }
    };

    fetchSettings();
  }, []);

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSettings(prev => ({ ...prev, [name]: value }));
    validateField(name, value);
  };

  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const numValue = parseInt(value, 10);
    
    if (value === '') {
      // Allow empty field while typing
      setSettings(prev => ({ ...prev, [name]: value }));
      validateField(name, value);
    } else if (!isNaN(numValue)) {
      setSettings(prev => ({ ...prev, [name]: numValue }));
      validateField(name, numValue.toString());
    }
  };

  const handleToggleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    
    // Check if confirmation is needed for this toggle
    if (requiresConfirmation(name, checked)) {
      openConfirmDialog(name, checked);
    } else {
      setSettings(prev => ({ ...prev, [name]: checked }));
    }
  };
  
  const requiresConfirmation = (fieldName: string, newValue: boolean): boolean => {
    // Add fields that need confirmation before changes
    switch (fieldName) {
      case 'maintenanceMode':
        return newValue === true;
      case 'allowNewRegistrations':
        return newValue === false;
      case 'notificationsEnabled':
        return newValue === false && settings.emailNotifications;
      default:
        return false;
    }
  };
  
  const openConfirmDialog = (fieldName: string, newValue: boolean) => {
    let title = 'Confirm Change';
    let message = 'Are you sure you want to change this setting?';
    
    // Customize confirmation message based on setting
    switch (fieldName) {
      case 'maintenanceMode':
        title = 'Enable Maintenance Mode?';
        message = 'Enabling maintenance mode will prevent regular users from accessing the application. Only administrators will have access until it is disabled.';
        break;
      case 'allowNewRegistrations':
        title = 'Disable New Registrations?';
        message = 'Disabling new registrations will prevent new users from creating accounts. Existing users will still be able to log in.';
        break;
      case 'notificationsEnabled':
        title = 'Disable All Notifications?';
        message = 'Disabling notifications will turn off all notification types, including email and push notifications for all users.';
        break;
    }
    
    setConfirmDialog({
      open: true,
      title,
      message,
      fieldName,
      newValue
    });
  };
  
  const handleConfirmDialogClose = () => {
    setConfirmDialog(prev => ({ ...prev, open: false }));
  };
  
  const handleConfirmDialogConfirm = () => {
    // Apply the change after confirmation
    setSettings(prev => ({ 
      ...prev, 
      [confirmDialog.fieldName]: confirmDialog.newValue 
    }));
    
    // Close the dialog
    handleConfirmDialogClose();
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const { name } = e.target;
    setTouched(prev => ({ ...prev, [name]: true }));
    validateField(name, settings[name as keyof typeof settings]);
  };

  const validateField = (name: string, value: any) => {
    let newErrors = { ...errors };
    
    switch (name) {
      case 'appTitle':
        if (!value || value.trim() === '') {
          newErrors.appTitle = 'Application title is required';
        } else if (value.length > 50) {
          newErrors.appTitle = 'Title must be less than 50 characters';
        } else {
          delete newErrors.appTitle;
        }
        break;
        
      case 'appDescription':
        if (value && value.length > 200) {
          newErrors.appDescription = 'Description must be less than 200 characters';
        } else {
          delete newErrors.appDescription;
        }
        break;
        
      case 'maxUploadSizeMB':
        if (value === '') {
          newErrors.maxUploadSizeMB = 'Max upload size is required';
        } else if (isNaN(Number(value))) {
          newErrors.maxUploadSizeMB = 'Must be a number';
        } else if (Number(value) < 1) {
          newErrors.maxUploadSizeMB = 'Must be at least 1 MB';
        } else if (Number(value) > 1000) {
          newErrors.maxUploadSizeMB = 'Must be less than 1000 MB';
        } else {
          delete newErrors.maxUploadSizeMB;
        }
        break;
        
      case 'rateLimit':
        if (value === '') {
          newErrors.rateLimit = 'Rate limit is required';
        } else if (isNaN(Number(value))) {
          newErrors.rateLimit = 'Must be a number';
        } else if (Number(value) < 10) {
          newErrors.rateLimit = 'Must be at least 10 requests per minute';
        } else if (Number(value) > 1000) {
          newErrors.rateLimit = 'Must be less than 1000 requests per minute';
        } else {
          delete newErrors.rateLimit;
        }
        break;
        
      default:
        break;
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateForm = () => {
    let newErrors: ValidationErrors = {};
    let isValid = true;
    
    // Validate app title
    if (!settings.appTitle || settings.appTitle.trim() === '') {
      newErrors.appTitle = 'Application title is required';
      isValid = false;
    } else if (settings.appTitle.length > 50) {
      newErrors.appTitle = 'Title must be less than 50 characters';
      isValid = false;
    }
    
    // Validate app description
    if (settings.appDescription && settings.appDescription.length > 200) {
      newErrors.appDescription = 'Description must be less than 200 characters';
      isValid = false;
    }
    
    // Validate max upload size
    if (typeof settings.maxUploadSizeMB === 'string' && settings.maxUploadSizeMB === '') {
      newErrors.maxUploadSizeMB = 'Max upload size is required';
      isValid = false;
    } else if (typeof settings.maxUploadSizeMB === 'number') {
      if (settings.maxUploadSizeMB < 1) {
        newErrors.maxUploadSizeMB = 'Must be at least 1 MB';
        isValid = false;
      } else if (settings.maxUploadSizeMB > 1000) {
        newErrors.maxUploadSizeMB = 'Must be less than 1000 MB';
        isValid = false;
      }
    }
    
    // Validate rate limit
    if (typeof settings.rateLimit === 'string' && settings.rateLimit === '') {
      newErrors.rateLimit = 'Rate limit is required';
      isValid = false;
    } else if (typeof settings.rateLimit === 'number') {
      if (settings.rateLimit < 10) {
        newErrors.rateLimit = 'Must be at least 10 requests per minute';
        isValid = false;
      } else if (settings.rateLimit > 1000) {
        newErrors.rateLimit = 'Must be less than 1000 requests per minute';
        isValid = false;
      }
    }
    
    setErrors(newErrors);
    // Mark all fields as touched when submitting
    const allTouched: Record<string, boolean> = {};
    Object.keys(newErrors).forEach(key => {
      allTouched[key] = true;
    });
    setTouched({ ...touched, ...allTouched });
    
    return isValid;
  };

  const handleSave = async () => {
    if (!validateForm()) {
      setError('Please fix the validation errors before saving.');
      return;
    }
    
    setIsSaving(true);
    setError(null);
    setSaved(false);
    
    try {
      // In production, this would be an API call
      // await api.put('/admin/settings', settings);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Error saving settings:', err);
      setError('Failed to save settings. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const renderSkeletonField = () => (
    <SkeletonLoader variant="rectangular" height="56px" borderRadius="4px" />
  );

  const renderSkeletonToggle = () => (
    <Box height="40px" display="flex" alignItems="center">
      <SkeletonLoader variant="rectangular" width="40px" height="24px" borderRadius="12px" />
      <LeftMarginSkeleton variant="text" width="120px" />
    </Box>
  );

  const showError = (field: keyof ValidationErrors) => {
    return touched[field] && errors[field] ? true : false;
  };

  return (
    <Container maxWidth="lg">
      <Box my={4}>
        {loading ? (
          <>
            <SkeletonLoader variant="text" width="40%" height="40px" />
            <BottomMarginSkeleton variant="text" width="60%" height="24px" />
          </>
        ) : (
          <>
            <Typography variant="h4" component="h1" gutterBottom>
              Application Settings
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              Configure application-wide settings
            </Typography>
          </>
        )}
        
        {saved && (
          <Alert severity="success" sx={{ mb: 3 }}>
            Settings saved successfully!
          </Alert>
        )}
        
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}
        
        <Paper elevation={2} sx={{ p: 3 }}>
          <Grid container spacing={3}>
            {/* General Settings */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                General Settings
              </Typography>
              <Divider sx={{ mb: 2 }} />
            </Grid>
            
            <Grid item xs={12} md={6}>
              {sectionLoading.general ? renderSkeletonField() : (
                <>
                  <TextField
                    fullWidth
                    label="Application Title"
                    name="appTitle"
                    value={settings.appTitle}
                    onChange={handleTextChange}
                    onBlur={handleBlur}
                    error={Boolean(touched.appTitle && errors.appTitle)}
                    helperText={touched.appTitle && errors.appTitle ? errors.appTitle : ''}
                    required
                  />
                </>
              )}
            </Grid>
            
            <Grid item xs={12} md={6}>
              {sectionLoading.general ? renderSkeletonField() : (
                <>
                  <TextField
                    fullWidth
                    label="Application Description"
                    name="appDescription"
                    value={settings.appDescription}
                    onChange={handleTextChange}
                    onBlur={handleBlur}
                    error={Boolean(touched.appDescription && errors.appDescription)}
                    helperText={touched.appDescription && errors.appDescription ? errors.appDescription : ''}
                    multiline
                    rows={2}
                  />
                </>
              )}
            </Grid>
            
            <Grid item xs={12} md={6}>
              {sectionLoading.general ? renderSkeletonToggle() : (
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.maintenanceMode}
                        onChange={handleToggleChange}
                        name="maintenanceMode"
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">Maintenance Mode</Typography>
                        {settings.maintenanceMode && (
                          <Typography variant="caption" color="error">
                            Active - Regular users cannot access the app
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                  <Typography variant="caption" color="text.secondary">
                    When enabled, only admins can access the application
                  </Typography>
                </FormGroup>
              )}
            </Grid>
            
            <Grid item xs={12} md={6}>
              {sectionLoading.general ? renderSkeletonToggle() : (
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.allowNewRegistrations}
                        onChange={handleToggleChange}
                        name="allowNewRegistrations"
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">Allow New Registrations</Typography>
                        {!settings.allowNewRegistrations && (
                          <Typography variant="caption" color="error">
                            Disabled - New users cannot register
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </FormGroup>
              )}
            </Grid>
            
            {/* Storage Settings */}
            <Grid item xs={12} sx={{ mt: 2 }}>
              <Typography variant="h6" gutterBottom>
                Storage Settings
              </Typography>
              <Divider sx={{ mb: 2 }} />
            </Grid>
            
            <Grid item xs={12} md={6}>
              {sectionLoading.storage ? renderSkeletonField() : (
                <TextField
                  select
                  fullWidth
                  label="Storage Provider"
                  name="storageProvider"
                  value={settings.storageProvider}
                  onChange={handleTextChange}
                  SelectProps={{
                    native: true
                  }}
                >
                  <option value="local">Local Storage</option>
                  <option value="s3">Amazon S3</option>
                </TextField>
              )}
            </Grid>
            
            <Grid item xs={12} md={6}>
              {sectionLoading.storage ? renderSkeletonField() : (
                <>
                  <TextField
                    fullWidth
                    type="number"
                    label="Max Upload Size (MB)"
                    name="maxUploadSizeMB"
                    value={settings.maxUploadSizeMB}
                    onChange={handleNumberChange}
                    onBlur={handleBlur}
                    error={Boolean(touched.maxUploadSizeMB && errors.maxUploadSizeMB)}
                    helperText={touched.maxUploadSizeMB && errors.maxUploadSizeMB ? errors.maxUploadSizeMB : ''}
                    inputProps={{ min: 1, max: 1000 }}
                    required
                  />
                </>
              )}
            </Grid>
            
            {/* Performance & Security */}
            <Grid item xs={12} sx={{ mt: 2 }}>
              <Typography variant="h6" gutterBottom>
                Performance & Security
              </Typography>
              <Divider sx={{ mb: 2 }} />
            </Grid>
            
            <Grid item xs={12} md={6}>
              {sectionLoading.security ? renderSkeletonField() : (
                <>
                  <TextField
                    fullWidth
                    type="number"
                    label="Rate Limit (requests per minute)"
                    name="rateLimit"
                    value={settings.rateLimit}
                    onChange={handleNumberChange}
                    onBlur={handleBlur}
                    error={Boolean(touched.rateLimit && errors.rateLimit)}
                    helperText={touched.rateLimit && errors.rateLimit ? errors.rateLimit : ''}
                    inputProps={{ min: 10, max: 1000 }}
                    required
                  />
                </>
              )}
            </Grid>
            
            <Grid item xs={12} md={6}>
              {sectionLoading.security ? renderSkeletonToggle() : (
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.analyticsEnabled}
                        onChange={handleToggleChange}
                        name="analyticsEnabled"
                      />
                    }
                    label="Enable Analytics"
                  />
                </FormGroup>
              )}
            </Grid>
            
            {/* Notifications */}
            <Grid item xs={12} sx={{ mt: 2 }}>
              <Typography variant="h6" gutterBottom>
                Notifications
              </Typography>
              <Divider sx={{ mb: 2 }} />
            </Grid>
            
            <Grid item xs={12} md={4}>
              {sectionLoading.notifications ? renderSkeletonToggle() : (
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.notificationsEnabled}
                        onChange={handleToggleChange}
                        name="notificationsEnabled"
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">Enable Notifications</Typography>
                        {!settings.notificationsEnabled && (
                          <Typography variant="caption" color="error">
                            All notifications disabled
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </FormGroup>
              )}
            </Grid>
            
            <Grid item xs={12} md={4}>
              {sectionLoading.notifications ? renderSkeletonToggle() : (
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.emailNotifications}
                        onChange={handleToggleChange}
                        name="emailNotifications"
                        disabled={!settings.notificationsEnabled}
                      />
                    }
                    label="Email Notifications"
                  />
                </FormGroup>
              )}
            </Grid>
            
            <Grid item xs={12} md={4}>
              {sectionLoading.notifications ? renderSkeletonToggle() : (
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.pushNotifications}
                        onChange={handleToggleChange}
                        name="pushNotifications"
                        disabled={!settings.notificationsEnabled}
                      />
                    }
                    label="Push Notifications"
                  />
                </FormGroup>
              )}
            </Grid>
            
            {/* Actions */}
            <Grid item xs={12} sx={{ mt: 3 }}>
              <Box display="flex" justifyContent="flex-end">
                {loading ? (
                  <SkeletonLoader variant="rectangular" width="140px" height="36px" borderRadius="4px" />
                ) : (
                  <Button 
                    variant="contained" 
                    color="primary" 
                    onClick={handleSave}
                    disabled={isSaving || Object.keys(errors).length > 0}
                    startIcon={isSaving ? <CircularProgress size={16} color="inherit" /> : null}
                  >
                    {isSaving ? 'Saving...' : 'Save Settings'}
                  </Button>
                )}
              </Box>
            </Grid>
          </Grid>
        </Paper>
      </Box>
      
      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onClose={handleConfirmDialogClose}
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
      >
        <DialogTitle id="confirm-dialog-title">{confirmDialog.title}</DialogTitle>
        <DialogContent>
          <DialogContentText id="confirm-dialog-description">
            {confirmDialog.message}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleConfirmDialogClose} color="primary">
            Cancel
          </Button>
          <Button onClick={handleConfirmDialogConfirm} color="error" variant="contained">
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}; 