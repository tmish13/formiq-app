# Frontend API Service

This directory contains service modules for interacting with the FormIQ API, with a focus on secure authentication using HttpOnly cookies and CSRF protection.

## API Service (`apiService.ts`)

The API service provides a secure and type-safe interface for interacting with the backend API. It handles:

- Authentication with HttpOnly cookies
- CSRF token management
- Response type handling
- Error standardization
- Request/response interceptors

## Core Features

### HttpOnly Cookie Support

The service is configured to work with cookies set by the backend:

```typescript
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,  // Important for HttpOnly cookies
});
```

### CSRF Protection

The service automatically manages CSRF tokens for non-GET requests:

```typescript
// Function to get CSRF token
const getCsrfToken = async (): Promise<string | null> => {
  try {
    // Check if we have a token cached
    if (csrfToken) return csrfToken;
    
    // Fetch new token
    const response = await api.get<CSRFTokenResponse>('/auth/csrf-token');
    csrfToken = response.data.csrf_token;
    return csrfToken;
  } catch (error) {
    console.error('Failed to fetch CSRF token:', error);
    return null;
  }
};

// Interceptor to add CSRF token to requests
api.interceptors.request.use(async (config) => {
  if (config.method !== 'get') {
    const token = await getCsrfToken();
    if (token) {
      config.headers['X-CSRF-Token'] = token;
    }
  }
  return config;
});
```

### Authentication Flow

The service provides methods for the complete authentication flow:

- `login(email, password)`: Authenticates user and receives HttpOnly cookies
- `register(userData)`: Registers new user
- `validateSession()`: Checks if current session is valid
- `logout()`: Clears authentication cookies
- `requestPasswordReset(email)`: Initiates password reset
- `resetPassword(token, password)`: Completes password reset
- `refreshToken()`: Refreshes access token using refresh token cookie
- `verifyEmail(token)`: Verifies user email with token

### User Profile Management

Methods for managing user profiles:

- `getCurrentUser()`: Gets current user details
- `updateProfile(data)`: Updates user profile data
- `updateAvatar(file)`: Updates user profile image

### Error Handling

Standardized error handling with proper typing:

```typescript
// Error handling interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle authentication errors
    if (error.response && error.response.status === 401) {
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    // Format error for consistent handling
    return Promise.reject({
      status: error.response?.status,
      message: error.response?.data?.detail || 'An error occurred',
      data: error.response?.data,
    } as ApiError);
  }
);
```

## Usage Examples

### User Authentication

```typescript
import { apiService } from '@/services/apiService';

// Login
const handleLogin = async (email: string, password: string) => {
  try {
    await apiService.login(email, password);
    // Redirect to dashboard on success
  } catch (error) {
    // Handle login error
  }
};

// Check if user is authenticated
const checkAuth = async () => {
  try {
    const isValid = await apiService.validateSession();
    if (!isValid) {
      // Redirect to login
    }
  } catch {
    // Handle error
  }
};
```

### Making API Requests

```typescript
import { apiService } from '@/services/apiService';

// GET request
const fetchData = async () => {
  try {
    const data = await apiService.get('/some-endpoint');
    return data;
  } catch (error) {
    // Handle error
  }
};

// POST request (CSRF token added automatically)
const createResource = async (data) => {
  try {
    const response = await apiService.post('/resource', data);
    return response;
  } catch (error) {
    // Handle error
  }
};
```

## Integration with React Components

This service works seamlessly with React hooks like `useAuth` to provide authentication state management throughout the application:

```typescript
export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const checkAuthStatus = async () => {
    try {
      const currentUser = await apiService.getCurrentUser();
      setUser(currentUser);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const login = async (email: string, password: string) => {
    await apiService.login(email, password);
    await checkAuthStatus();
  };

  const logout = async () => {
    await apiService.logout();
    setUser(null);
  };

  return {
    user,
    loading,
    login,
    logout,
    checkAuthStatus,
  };
};
```

## Security Considerations

This implementation follows security best practices:

1. **No tokens in localStorage**: Tokens are stored exclusively in HttpOnly cookies
2. **CSRF protection**: All state-changing requests include CSRF tokens
3. **Automatic token refresh**: Handles token expiration transparently
4. **Proper error handling**: Standardized error formatting for consistent UX
5. **Automatic redirects**: Routes users to login when authentication fails

## Related Files

- `types/auth.ts`: Type definitions for authentication-related data
- `hooks/useAuth.ts`: React hook for authentication state management
- `config/constants.ts`: API URL and other configuration constants
 