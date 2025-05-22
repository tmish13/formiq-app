/**
 * Consolidated Tests for API Interactions and Network Features
 * 
 * This file tests user interactions with network-dependent features:
 * 1. Loading and displaying data from APIs
 * 2. Handling network errors and offline states
 * 3. User authentication flows
 * 4. Form submissions and data persistence
 */
import React, { useEffect, useState } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { http, HttpResponse } from 'msw';

// Import shared testing utilities
import { 
  setupMockServer, 
  setupServerLifecycle,
  createMockUser,
  createMockFormCheck,
  createMockFormChecks,
  authHandlers,
  formCheckHandlers
} from '../utils/sharedMocks';

// Define types for the application
interface UserProfile {
  id: string;
  name: string;
  email: string;
  profileImage: string;
  subscription: string;
  stats: {
    formChecksCompleted: number;
    averageScore: number;
  };
}

interface FormCheck {
  id: string;
  user_id: string;
  exercise_type: string;
  video_url: string;
  status: string;
  score: number;
  created_at: string;
  updated_at: string;
}

interface Exercise {
  id: string;
  name: string;
  category: string;
  difficulty: string;
}

// API test handlers
const customHandlers = [
  // Health check endpoint
  http.get('/api/health', () => {
    return HttpResponse.json({ status: 'ok' });
  }),
  
  // User profile endpoint
  http.get('/api/users/:userId', ({ params }) => {
    if (params.userId === 'invalid-id') {
      return new HttpResponse(null, { status: 404 });
    }
    
    return HttpResponse.json({
      id: params.userId,
      name: 'Test User',
      email: 'test@example.com',
      profileImage: 'https://example.com/profile.jpg',
      subscription: 'premium',
      stats: {
        formChecksCompleted: 12,
        averageScore: 85
      }
    });
  }),
  
  // Exercises library endpoints
  http.get('/api/exercises', ({ request }) => {
    const url = new URL(request.url);
    const category = url.searchParams.get('category');
    
    const exercises = [
      { id: 'ex1', name: 'Squat', category: 'Lower Body', difficulty: 'Beginner' },
      { id: 'ex2', name: 'Deadlift', category: 'Lower Body', difficulty: 'Intermediate' },
      { id: 'ex3', name: 'Bench Press', category: 'Upper Body', difficulty: 'Intermediate' },
      { id: 'ex4', name: 'Pull-up', category: 'Upper Body', difficulty: 'Advanced' },
      { id: 'ex5', name: 'Plank', category: 'Core', difficulty: 'Beginner' }
    ];
    
    if (category) {
      return HttpResponse.json({
        items: exercises.filter(ex => ex.category === category)
      });
    }
    
    return HttpResponse.json({ items: exercises });
  }),
  
  // Workouts endpoints
  http.get('/api/workouts', () => {
    return HttpResponse.json({
      items: [
        { id: 'w1', name: 'Full Body Strength', exercises: ['ex1', 'ex3', 'ex5'] },
        { id: 'w2', name: 'Lower Body Focus', exercises: ['ex1', 'ex2'] },
        { id: 'w3', name: 'Core Blast', exercises: ['ex5'] }
      ]
    });
  }),
  
  // Error endpoint for testing error handling
  http.get('/api/error', () => {
    return new HttpResponse(null, { status: 500 });
  })
];

// Setup mock server
const server = setupMockServer([
  ...authHandlers,
  ...formCheckHandlers,
  ...customHandlers
]);
setupServerLifecycle(server);

/**
 * API Interaction Tests
 */
describe('User Interactions with Network-Dependent Features', () => {
  beforeEach(() => {
    localStorage.clear();
  });
  
  /**
   * API Health Check Component
   */
  const ApiHealthCheck = () => {
    const [apiStatus, setApiStatus] = useState<'unknown' | 'online' | 'offline'>('unknown');
      const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
      
    const checkApiStatus = async () => {
          setIsLoading(true);
          setError(null);
          
          try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        setApiStatus(data.status === 'ok' ? 'online' : 'offline');
          } catch (err) {
        setApiStatus('offline');
        setError('Could not connect to the API');
          } finally {
            setIsLoading(false);
          }
        };
      
      return (
        <div>
        <h1>API Status</h1>
        <button 
          onClick={checkApiStatus} 
          disabled={isLoading}
          data-testid="check-api-btn"
        >
          Check API Status
        </button>
        
        {isLoading && <p data-testid="loading-indicator">Loading...</p>}
        
        {apiStatus !== 'unknown' && !isLoading && (
          <div data-testid="api-status" className={apiStatus}>
            API is {apiStatus}
          </div>
        )}
        
        {error && <p data-testid="error-message" role="alert">{error}</p>}
      </div>
    );
  };
  
  /**
   * User Profile Component
   */
  const UserProfile = () => {
    const [userId, setUserId] = useState('');
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    const fetchProfile = async () => {
      if (!userId.trim()) {
        setError('Please enter a user ID');
        return;
      }
      
      setIsLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`/api/users/${userId}`);
        if (response.ok) {
          const data = await response.json();
          setProfile(data);
        } else {
          throw new Error('User not found');
        }
      } catch (err) {
        setError('Failed to load user profile');
      } finally {
        setIsLoading(false);
      }
    };
    
    return (
      <div>
        <h1>User Profile</h1>
        <div>
          <label htmlFor="user-id">User ID</label>
          <input
            id="user-id"
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Enter user ID"
            data-testid="user-id-input"
          />
          <button
            onClick={fetchProfile}
            disabled={isLoading}
            data-testid="fetch-profile-btn"
          >
            Fetch Profile
          </button>
        </div>
        
        {isLoading && <p data-testid="loading-indicator">Loading profile...</p>}
        
        {error && <p data-testid="error-message" role="alert">{error}</p>}
        
        {profile && (
          <div data-testid="user-profile">
            <h2>{profile.name}</h2>
            <p>Email: {profile.email}</p>
            <p>Subscription: {profile.subscription}</p>
            <div>
              <h3>Stats</h3>
              <p>Completed Form Checks: {profile.stats.formChecksCompleted}</p>
              <p>Average Score: {profile.stats.averageScore}</p>
            </div>
          </div>
        )}
      </div>
    );
  };
  
  /**
   * Form Check List Component
   */
  const FormCheckList = () => {
    const [formChecks, setFormChecks] = useState<FormCheck[]>([]);
    const [isLoading, setIsLoading] = useState(false);
      const [error, setError] = useState<string | null>(null);
      
      const loadFormChecks = async () => {
      setIsLoading(true);
        setError(null);
        
        try {
        const response = await fetch('/api/form-checks');
        const data = await response.json();
        
        // Handle different response formats
        const checks = Array.isArray(data) ? data : data.items || [];
        setFormChecks(checks);
        } catch (err) {
        setError('Failed to load form checks');
        } finally {
        setIsLoading(false);
      }
    };
    
    const deleteFormCheck = async (id: string) => {
      try {
        await fetch(`/api/form-checks/${id}`, {
          method: 'DELETE'
        });
        // Remove from local state on success
        setFormChecks(formChecks.filter(check => check.id !== id));
      } catch (err) {
        setError('Failed to delete form check');
      }
    };
    
    // Load form checks on mount
    useEffect(() => {
      loadFormChecks();
    }, []);
      
      return (
        <div>
        <h1>Form Check History</h1>
        
        {isLoading && <p data-testid="loading-indicator">Loading form checks...</p>}
        
        {error && <p data-testid="error-message" role="alert">{error}</p>}
        
        {formChecks.length > 0 ? (
          <ul data-testid="form-check-list">
            {formChecks.map(check => (
              <li key={check.id} data-testid={`form-check-${check.id}`}>
                <div>Exercise: {check.exercise_type}</div>
                <div>Status: {check.status}</div>
                {check.score && <div>Score: {check.score}</div>}
                <button
                  onClick={() => deleteFormCheck(check.id.toString())}
                  data-testid={`delete-btn-${check.id}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        ) : !isLoading && (
          <p data-testid="empty-message">No form checks found</p>
        )}
        
        <button
          onClick={loadFormChecks}
          disabled={isLoading}
          data-testid="refresh-btn"
        >
          Refresh
        </button>
          </div>
        );
      };
  
  /**
   * Login Form Component
   */
  const LoginForm = () => {
    const [credentials, setCredentials] = useState({
      email: '',
      password: ''
    });
    const [isLoading, setIsLoading] = useState(false);
      const [error, setError] = useState<string | null>(null);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [user, setUser] = useState<any>(null);
      
      const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
      setIsLoading(true);
        setError(null);
        
        try {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(credentials)
        });
        
        if (response.ok) {
          const data = await response.json();
          // Store token in localStorage (in a real app, consider more secure options)
          localStorage.setItem('token', data.token);
          setIsLoggedIn(true);
          setUser(data.user);
        } else {
          const errorData = await response.json();
          throw new Error(errorData.message || 'Login failed');
        }
        } catch (err) {
        setError(err instanceof Error ? err.message : 'Login failed');
        } finally {
        setIsLoading(false);
      }
    };
    
    const handleLogout = () => {
      localStorage.removeItem('token');
      setIsLoggedIn(false);
      setUser(null);
    };
    
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const { name, value } = e.target;
      setCredentials(prev => ({
        ...prev,
        [name]: value
      }));
    };
    
    if (isLoggedIn) {
      return (
        <div data-testid="logged-in-view">
          <h2>Welcome, {user.name || user.email}</h2>
          <button onClick={handleLogout} data-testid="logout-btn">
            Logout
          </button>
        </div>
      );
    }
      
      return (
        <div>
        <h1>Login</h1>
          
        <form onSubmit={handleLogin}>
            <div>
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
              name="email"
              value={credentials.email}
              onChange={handleChange}
                required
              data-testid="email-input"
              />
            </div>
            
            <div>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
              name="password"
              value={credentials.password}
              onChange={handleChange}
                required
              data-testid="password-input"
              />
            </div>
            
          <button
            type="submit"
            disabled={isLoading}
            data-testid="login-btn"
          >
            {isLoading ? 'Logging in...' : 'Login'}
            </button>
          </form>
        
        {error && <p data-testid="error-message" role="alert">{error}</p>}
        </div>
      );
    };

  /**
   * Exercise Library Component
   */
  const ExerciseLibrary = () => {
    const [exercises, setExercises] = useState<Exercise[]>([]);
    const [selectedCategory, setSelectedCategory] = useState('');
    const [isLoading, setIsLoading] = useState(false);
      const [error, setError] = useState<string | null>(null);
      
    const loadExercises = async (category = '') => {
      setIsLoading(true);
        setError(null);
        
        try {
        const url = category
          ? `/api/exercises?category=${encodeURIComponent(category)}`
          : '/api/exercises';
          
        const response = await fetch(url);
        const data = await response.json();
        
        setExercises(data.items as Exercise[]);
        } catch (err) {
        setError('Failed to load exercises');
        } finally {
        setIsLoading(false);
      }
    };
    
    useEffect(() => {
      loadExercises();
    }, []);
    
    const handleCategoryChange = (category: string) => {
      setSelectedCategory(category);
      loadExercises(category);
      };
      
      return (
        <div>
        <h1>Exercise Library</h1>
          
          <div>
          <label htmlFor="category-filter">Filter by Category</label>
          <select
            id="category-filter"
            value={selectedCategory}
            onChange={(e) => handleCategoryChange(e.target.value)}
            data-testid="category-filter"
          >
            <option value="">All Categories</option>
            <option value="Lower Body">Lower Body</option>
            <option value="Upper Body">Upper Body</option>
            <option value="Core">Core</option>
          </select>
          </div>
          
        {isLoading && <p data-testid="loading-indicator">Loading exercises...</p>}
          
        {error && <p data-testid="error-message" role="alert">{error}</p>}
        
        {exercises.length > 0 ? (
          <ul data-testid="exercise-list">
            {exercises.map(exercise => (
              <li key={exercise.id} data-testid={`exercise-${exercise.id}`}>
                <h3>{exercise.name}</h3>
                <p>Category: {exercise.category}</p>
                <p>Difficulty: {exercise.difficulty}</p>
              </li>
            ))}
          </ul>
        ) : !isLoading && (
          <p data-testid="empty-message">No exercises found</p>
        )}
        </div>
      );
    };
    
  // Tests for API Health Check
  describe('API Health Check', () => {
    it('GIVEN the API is online WHEN a user checks the API status THEN they see the API is online', async () => {
      const user = userEvent.setup();
      render(<ApiHealthCheck />);
      
      // Click the check API button
      await user.click(screen.getByTestId('check-api-btn'));
      
      // Verify loading state appears
      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
      
      // Verify status shows online
      await waitFor(() => {
        expect(screen.getByTestId('api-status')).toHaveTextContent('API is online');
      });
    });
    
    it('GIVEN the API is down WHEN a user checks the API status THEN they see an error message', async () => {
      // Override the handler to return an error
      server.use(
        http.get('/api/health', () => {
          return new HttpResponse(null, { status: 500 });
        })
      );
      
      const user = userEvent.setup();
      render(<ApiHealthCheck />);
      
      // Click the check API button
      await user.click(screen.getByTestId('check-api-btn'));
      
      // Verify error message appears
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });
    });
  });

  // Tests for User Profile
  describe('User Profile', () => {
    it('GIVEN a valid user ID WHEN a user fetches a profile THEN they see the user details', async () => {
      const user = userEvent.setup();
      render(<UserProfile />);
      
      // Enter a valid user ID
      await user.type(screen.getByTestId('user-id-input'), 'user-123');
      
      // Click the fetch button
      await user.click(screen.getByTestId('fetch-profile-btn'));
      
      // Verify loading state appears
      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
      
      // Verify profile details are displayed
      await waitFor(() => {
        expect(screen.getByTestId('user-profile')).toBeInTheDocument();
        expect(screen.getByTestId('user-profile')).toHaveTextContent('Test User');
        expect(screen.getByTestId('user-profile')).toHaveTextContent('test@example.com');
      });
    });
    
    it('GIVEN an invalid user ID WHEN a user fetches a profile THEN they see an error message', async () => {
      const user = userEvent.setup();
      render(<UserProfile />);
      
      // Enter an invalid user ID
      await user.type(screen.getByTestId('user-id-input'), 'invalid-id');
      
      // Click the fetch button
      await user.click(screen.getByTestId('fetch-profile-btn'));
      
      // Verify error message appears
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });
    });
    
    it('GIVEN an empty user ID WHEN a user fetches a profile THEN they see a validation error', async () => {
      const user = userEvent.setup();
      render(<UserProfile />);
      
      // Click the fetch button without entering a user ID
      await user.click(screen.getByTestId('fetch-profile-btn'));
      
      // Verify error message appears
      expect(screen.getByTestId('error-message')).toHaveTextContent('Please enter a user ID');
    });
  });
  
  // Tests for Form Check List
  describe('Form Check History', () => {
    it('GIVEN a user has submitted form checks WHEN they view their history THEN they see all their previous submissions', async () => {
      render(<FormCheckList />);
      
      // Verify loading state appears
      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
      
      // Verify form checks are displayed
      await waitFor(() => {
        const formCheckList = screen.getByTestId('form-check-list');
        expect(formCheckList).toBeInTheDocument();
        expect(formCheckList.children.length).toBeGreaterThan(0);
      });
    });
    
    it('GIVEN a user has form checks WHEN they delete one THEN it is removed from the list', async () => {
      const user = userEvent.setup();
      render(<FormCheckList />);
      
      // Wait for form checks to load
      await waitFor(() => {
        expect(screen.getByTestId('form-check-list')).toBeInTheDocument();
      });
      
      // Get the first delete button
      const deleteButton = screen.getByTestId(/delete-btn-/);
      const formCheckItem = deleteButton.closest('li');
      const formCheckId = formCheckItem?.getAttribute('data-testid')?.replace('form-check-', '');
      
      // Click the delete button
      await user.click(deleteButton);
      
      // Verify the form check is removed
      await waitFor(() => {
        expect(screen.queryByTestId(`form-check-${formCheckId}`)).not.toBeInTheDocument();
      });
    });
  });

  // Tests for Login Form
  describe('User Authentication', () => {
    it('GIVEN valid credentials WHEN a user logs in THEN they are authenticated and see a welcome message', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      // Enter valid credentials
      await user.type(screen.getByTestId('email-input'), 'valid@example.com');
      await user.type(screen.getByTestId('password-input'), 'password123');
      
      // Submit the form
      await user.click(screen.getByTestId('login-btn'));
      
      // Verify login was successful
      await waitFor(() => {
        expect(screen.getByTestId('logged-in-view')).toBeInTheDocument();
        expect(screen.getByTestId('logged-in-view')).toHaveTextContent(/welcome/i);
      });
    });
    
    it('GIVEN invalid credentials WHEN a user logs in THEN they see an error message', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      // Enter invalid credentials
      await user.type(screen.getByTestId('email-input'), 'invalid@example.com');
      await user.type(screen.getByTestId('password-input'), 'wrongpassword');
      
      // Submit the form
      await user.click(screen.getByTestId('login-btn'));
      
      // Verify error message appears
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      });
    });
    
    it('GIVEN a logged in user WHEN they log out THEN they return to the login form', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      // Login first
      await user.type(screen.getByTestId('email-input'), 'valid@example.com');
      await user.type(screen.getByTestId('password-input'), 'password123');
      await user.click(screen.getByTestId('login-btn'));
      
      // Wait for login to complete
      await waitFor(() => {
        expect(screen.getByTestId('logged-in-view')).toBeInTheDocument();
      });
      
      // Click logout
      await user.click(screen.getByTestId('logout-btn'));
      
      // Verify user is logged out and login form is displayed
      expect(screen.getByTestId('login-btn')).toBeInTheDocument();
      expect(screen.queryByTestId('logged-in-view')).not.toBeInTheDocument();
    });
  });
  
  // Tests for Exercise Library
  describe('Exercise Library', () => {
    it('GIVEN the exercise library is loaded WHEN a user views the library THEN they see all exercises', async () => {
      render(<ExerciseLibrary />);
      
      // Verify loading state appears
      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
      
      // Verify exercises are displayed
      await waitFor(() => {
        const exerciseList = screen.getByTestId('exercise-list');
        expect(exerciseList).toBeInTheDocument();
        expect(exerciseList.children.length).toBeGreaterThan(0);
      });
    });
    
    it('GIVEN the exercise library is loaded WHEN a user filters by category THEN they only see exercises in that category', async () => {
      const user = userEvent.setup();
      render(<ExerciseLibrary />);
      
      // Wait for exercises to load
      await waitFor(() => {
        expect(screen.getByTestId('exercise-list')).toBeInTheDocument();
      });
      
      // Select a category filter
      await user.selectOptions(screen.getByTestId('category-filter'), 'Lower Body');
      
      // Verify loading state appears
      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
      
      // Verify only Lower Body exercises are displayed
      await waitFor(() => {
        const exerciseList = screen.getByTestId('exercise-list');
        expect(exerciseList).toBeInTheDocument();
        
        // Check that all displayed exercises are in the Lower Body category
        const exercises = screen.getAllByText(/Category: Lower Body/i);
        expect(exercises.length).toBeGreaterThan(0);
        expect(exercises.length).toBe(exerciseList.children.length);
      });
    });
  });
}); 