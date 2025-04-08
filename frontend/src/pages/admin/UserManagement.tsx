import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Typography, 
  Box, 
  Paper, 
  Button, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  Snackbar,
  Alert,
  IconButton,
  useMediaQuery,
  useTheme
} from '@mui/material';
import SkeletonLoader from '../../components/common/SkeletonLoader';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import PersonAddIcon from '@mui/icons-material/PersonAdd';

// Mock user data - will be replaced with API calls in production
const mockUsers = [
  { id: 1, name: 'John Doe', email: 'john@example.com', role: 'user', status: 'active' },
  { id: 2, name: 'Jane Smith', email: 'jane@example.com', role: 'admin', status: 'active' },
  { id: 3, name: 'Bob Johnson', email: 'bob@example.com', role: 'user', status: 'inactive' },
  { id: 4, name: 'Alice Williams', email: 'alice@example.com', role: 'user', status: 'active' },
];

// User form data type
interface UserFormData {
  id?: number;
  name: string;
  email: string;
  role: string;
  status: string;
  password?: string;
}

// Empty user form for new users
const emptyUserForm: UserFormData = {
  name: '',
  email: '',
  role: 'user',
  status: 'active',
  password: ''
};

export const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  
  // Dialog and form states
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [userFormOpen, setUserFormOpen] = useState(false);
  const [userForm, setUserForm] = useState<UserFormData>(emptyUserForm);
  const [isNewUser, setIsNewUser] = useState(false);
  const [formErrors, setFormErrors] = useState<{[key: string]: string}>({});
  
  // Material UI theme and media query for responsive design
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  // Notification states
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error' | 'info' | 'warning'
  });

  useEffect(() => {
    // Simulate API fetch
    const fetchUsers = async () => {
      try {
        // In production, this would be an API call
        // const response = await api.get('/users');
        // setUsers(response.data);
        
        // Simulate network delay
        setTimeout(() => {
          setUsers(mockUsers);
          setLoading(false);
        }, 1500);
      } catch (error) {
        console.error('Error fetching users:', error);
        setLoading(false);
        showSnackbar('Failed to load users', 'error');
      }
    };

    fetchUsers();
  }, []);

  const handleStatusToggle = (userId: number) => {
    setUsers(users.map(user => {
      if (user.id === userId) {
        const newStatus = user.status === 'active' ? 'inactive' : 'active';
        showSnackbar(`User ${user.name} ${newStatus === 'active' ? 'activated' : 'deactivated'}`, 'info');
        return { ...user, status: newStatus };
      }
      return user;
    }));
  };

  const handleRoleToggle = (userId: number) => {
    setUsers(users.map(user => {
      if (user.id === userId) {
        const newRole = user.role === 'user' ? 'admin' : 'user';
        showSnackbar(`${user.name} role changed to ${newRole}`, 'info');
        return { ...user, role: newRole };
      }
      return user;
    }));
  };
  
  // Delete dialog handlers
  const openDeleteDialog = (userId: number) => {
    setSelectedUserId(userId);
    setDeleteDialogOpen(true);
  };
  
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setSelectedUserId(null);
  };
  
  const handleDeleteUser = () => {
    if (selectedUserId) {
      const userToDelete = users.find(user => user.id === selectedUserId);
      setUsers(users.filter(user => user.id !== selectedUserId));
      showSnackbar(`User ${userToDelete.name} deleted successfully`, 'success');
      closeDeleteDialog();
    }
  };
  
  // User form handlers
  const openEditUserForm = (userId: number) => {
    const userToEdit = users.find(user => user.id === userId);
    if (userToEdit) {
      setUserForm({
        id: userToEdit.id,
        name: userToEdit.name,
        email: userToEdit.email,
        role: userToEdit.role,
        status: userToEdit.status
      });
      setIsNewUser(false);
      setUserFormOpen(true);
      setFormErrors({});
    }
  };
  
  const openNewUserForm = () => {
    setUserForm(emptyUserForm);
    setIsNewUser(true);
    setUserFormOpen(true);
    setFormErrors({});
  };
  
  const closeUserForm = () => {
    setUserFormOpen(false);
  };
  
  const handleUserFormChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setUserForm(prev => ({ ...prev, [name]: value }));
    
    // Clear error for this field when user types
    if (formErrors[name]) {
      setFormErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };
  
  const validateUserForm = (): boolean => {
    const errors: {[key: string]: string} = {};
    
    if (!userForm.name.trim()) {
      errors.name = 'Name is required';
    }
    
    if (!userForm.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(userForm.email)) {
      errors.email = 'Email is invalid';
    }
    
    if (isNewUser && (!userForm.password || userForm.password.length < 6)) {
      errors.password = 'Password must be at least 6 characters';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };
  
  const handleSaveUser = () => {
    if (!validateUserForm()) {
      return;
    }
    
    if (isNewUser) {
      // Generate a fake ID for mock data
      const newId = Math.max(...users.map(u => u.id), 0) + 1;
      const newUser = {
        id: newId,
        name: userForm.name,
        email: userForm.email,
        role: userForm.role,
        status: userForm.status
      };
      setUsers([...users, newUser]);
      showSnackbar(`User ${userForm.name} created successfully`, 'success');
    } else {
      setUsers(users.map(user => 
        user.id === userForm.id ? { ...userForm } : user
      ));
      showSnackbar(`User ${userForm.name} updated successfully`, 'success');
    }
    
    closeUserForm();
  };
  
  // Snackbar handlers
  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info' | 'warning') => {
    setSnackbar({
      open: true,
      message,
      severity
    });
  };
  
  const handleCloseSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  return (
    <Container maxWidth="lg">
      <Box my={4}>
        {loading ? (
          <>
            <SkeletonLoader variant="text" width="30%" height="40px" />
            <SkeletonLoader variant="text" width="70%" height="24px" />
            <Box mb={3} display="flex" justifyContent="flex-end">
              <SkeletonLoader variant="rectangular" width="120px" height="36px" />
            </Box>
          </>
        ) : (
          <>
            <Typography variant="h4" component="h1" gutterBottom>
              User Management
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              Manage user accounts, roles, and permissions
            </Typography>
            
            <Box mb={3} display="flex" justifyContent="flex-end">
              <Button 
                variant="contained" 
                color="primary" 
                startIcon={<PersonAddIcon />}
                onClick={openNewUserForm}
              >
                Add New User
              </Button>
            </Box>
          </>
        )}
        
        <Paper elevation={2}>
          <TableContainer>
            <Table size={isMobile ? "small" : "medium"}>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  {!isMobile && <TableCell>Email</TableCell>}
                  {!isMobile && <TableCell>Role</TableCell>}
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  // Skeleton rows for loading state
                  Array.from({ length: 4 }).map((_, index) => (
                    <TableRow key={index}>
                      <TableCell><SkeletonLoader variant="text" width="80%" /></TableCell>
                      {!isMobile && <TableCell><SkeletonLoader variant="text" width="90%" /></TableCell>}
                      {!isMobile && <TableCell><SkeletonLoader variant="rectangular" width="60px" height="24px" borderRadius="16px" /></TableCell>}
                      <TableCell><SkeletonLoader variant="rectangular" width="70px" height="24px" borderRadius="16px" /></TableCell>
                      <TableCell>
                        <Box display="flex" gap={1}>
                          <SkeletonLoader variant="rectangular" width="40px" height="30px" />
                          <SkeletonLoader variant="rectangular" width="60px" height="30px" />
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  users.map(user => (
                    <TableRow key={user.id}>
                      <TableCell>
                        {user.name}
                        {isMobile && (
                          <Typography variant="caption" color="textSecondary" component="div">
                            {user.email}
                          </Typography>
                        )}
                      </TableCell>
                      {!isMobile && <TableCell>{user.email}</TableCell>}
                      {!isMobile && (
                        <TableCell>
                          <Chip 
                            label={user.role}
                            color={user.role === 'admin' ? 'secondary' : 'default'}
                            size="small"
                            onClick={() => handleRoleToggle(user.id)}
                          />
                        </TableCell>
                      )}
                      <TableCell>
                        <Chip 
                          label={user.status}
                          color={user.status === 'active' ? 'success' : 'error'}
                          size="small"
                          onClick={() => handleStatusToggle(user.id)}
                        />
                        {isMobile && (
                          <Chip 
                            label={user.role}
                            color={user.role === 'admin' ? 'secondary' : 'default'}
                            size="small"
                            onClick={() => handleRoleToggle(user.id)}
                            sx={{ ml: 1 }}
                          />
                        )}
                      </TableCell>
                      <TableCell>
                        <Box display="flex" gap={1}>
                          <IconButton 
                            size="small" 
                            color="primary"
                            onClick={() => openEditUserForm(user.id)}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                          
                          <IconButton 
                            size="small" 
                            color="error"
                            onClick={() => openDeleteDialog(user.id)}
                            disabled={user.id === 2} // Prevent deleting the admin user in this demo
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </Box>
      
      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={closeDeleteDialog}
      >
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this user? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDeleteDialog} color="primary">
            Cancel
          </Button>
          <Button onClick={handleDeleteUser} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* User Form Dialog */}
      <Dialog
        open={userFormOpen}
        onClose={closeUserForm}
        maxWidth="sm"
        fullWidth
        fullScreen={isMobile}
      >
        <DialogTitle>{isNewUser ? 'Add New User' : 'Edit User'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              fullWidth
              margin="normal"
              label="Name"
              name="name"
              value={userForm.name}
              onChange={handleUserFormChange}
              error={Boolean(formErrors.name)}
              helperText={formErrors.name}
              required
            />
            
            <TextField
              fullWidth
              margin="normal"
              label="Email"
              name="email"
              type="email"
              value={userForm.email}
              onChange={handleUserFormChange}
              error={Boolean(formErrors.email)}
              helperText={formErrors.email}
              required
            />
            
            {isNewUser && (
              <TextField
                fullWidth
                margin="normal"
                label="Password"
                name="password"
                type="password"
                value={userForm.password}
                onChange={handleUserFormChange}
                error={Boolean(formErrors.password)}
                helperText={formErrors.password}
                required
              />
            )}
            
            <TextField
              fullWidth
              margin="normal"
              label="Role"
              name="role"
              select
              SelectProps={{ native: true }}
              value={userForm.role}
              onChange={handleUserFormChange}
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </TextField>
            
            <TextField
              fullWidth
              margin="normal"
              label="Status"
              name="status"
              select
              SelectProps={{ native: true }}
              value={userForm.status}
              onChange={handleUserFormChange}
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeUserForm} color="primary">
            Cancel
          </Button>
          <Button onClick={handleSaveUser} color="primary" variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}; 