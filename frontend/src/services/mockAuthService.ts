/**
 * Mock Authentication Service for Development
 * Provides local authentication functionality when backend is not available
 */

import { User } from '../types/user';

interface MockUser {
  id: string;
  email: string;
  password: string;
  name: string;
  role: 'user' | 'admin' | 'trainer';
  isActive: boolean;
  isVerified: boolean;
  subscriptionTier: 'free' | 'basic' | 'premium';
  isEmailVerified: boolean;
  has_completed_onboarding: boolean;
  onboarding_completed_at?: string;
  createdAt: string;
  updatedAt: string;
}

interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
}

class MockAuthService {
  private readonly STORAGE_KEY = 'formiq_mock_users';
  private readonly CURRENT_USER_KEY = 'formiq_current_user';

  constructor() {
    this.initializeDefaultUsers();
  }

  private initializeDefaultUsers() {
    const existingUsers = this.getStoredUsers();
    if (existingUsers.length === 0) {
      const defaultUsers: MockUser[] = [
        {
          id: '1',
          email: 'demo@formiq.com',
          password: 'password123',
          name: 'Demo User',
          role: 'user',
          isActive: true,
          isVerified: true,
          subscriptionTier: 'free',
          isEmailVerified: true,
          has_completed_onboarding: false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
        {
          id: '2',
          email: 'trainer@formiq.com',
          password: 'trainer123',
          name: 'Professional Trainer',
          role: 'trainer',
          isActive: true,
          isVerified: true,
          subscriptionTier: 'premium',
          isEmailVerified: true,
          has_completed_onboarding: true,
          onboarding_completed_at: new Date().toISOString(),
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        },
        {
          id: '3',
          email: 'john@example.com',
          password: 'password123',
          name: 'John Smith',
          role: 'user',
          isActive: true,
          isVerified: true,
          subscriptionTier: 'basic',
          isEmailVerified: true,
          has_completed_onboarding: true,
          onboarding_completed_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
          createdAt: new Date(Date.now() - 86400000 * 7).toISOString(), // 1 week ago
          updatedAt: new Date().toISOString(),
        }
      ];
      this.storeUsers(defaultUsers);
    }
  }

  private getStoredUsers(): MockUser[] {
    try {
      const users = localStorage.getItem(this.STORAGE_KEY);
      return users ? JSON.parse(users) : [];
    } catch (error) {
      console.error('Error reading stored users:', error);
      return [];
    }
  }

  private storeUsers(users: MockUser[]): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(users));
    } catch (error) {
      console.error('Error storing users:', error);
    }
  }

  private findUserByEmail(email: string): MockUser | null {
    const users = this.getStoredUsers();
    return users.find(user => user.email.toLowerCase() === email.toLowerCase()) || null;
  }

  private generateToken(): string {
    return `mock_token_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private convertToUser(mockUser: MockUser): User {
    const { password, ...user } = mockUser;
    return user as User;
  }

  // Simulate API delay
  private async delay(ms: number = 1000): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Mock login function
   */
  async login(email: string, password: string): Promise<AuthResponse> {
    await this.delay();

    console.log(`🔐 Attempting login for: ${email}`);
    
    const user = this.findUserByEmail(email);
    if (!user) {
      console.log(`❌ User not found: ${email}`);
      console.log(`📋 Available users:`, this.getStoredUsers().map(u => u.email));
      throw new Error('User not found');
    }

    console.log(`✅ User found: ${email}`);

    if (user.password !== password) {
      console.log(`❌ Invalid password for: ${email}`);
      throw new Error('Invalid password');
    }

    console.log(`✅ Password correct for: ${email}`);

    if (!user.isActive) {
      console.log(`❌ Account deactivated for: ${email}`);
      throw new Error('Account is deactivated');
    }

    const tokens = {
      access_token: this.generateToken(),
      refresh_token: this.generateToken(),
    };

    // Store current user session
    localStorage.setItem(this.CURRENT_USER_KEY, JSON.stringify({
      user: this.convertToUser(user),
      ...tokens
    }));

    return {
      user: this.convertToUser(user),
      ...tokens
    };
  }

  /**
   * Mock register function
   */
  async register(userData: {
    email: string;
    password: string;
    confirm_password: string;
    username?: string;
    first_name?: string;
    last_name?: string;
  }): Promise<AuthResponse> {
    await this.delay();

    // Validate input
    if (userData.password !== userData.confirm_password) {
      throw new Error('Passwords do not match');
    }

    if (this.findUserByEmail(userData.email)) {
      throw new Error('Email already registered');
    }

    // Create new user
    const users = this.getStoredUsers();
    const newUser: MockUser = {
      id: (users.length + 1).toString(),
      email: userData.email,
      password: userData.password,
      name: userData.first_name && userData.last_name 
        ? `${userData.first_name} ${userData.last_name}` 
        : userData.email.split('@')[0],
      role: 'user',
      isActive: true,
      isVerified: true,
      subscriptionTier: 'free',
      isEmailVerified: true,
      has_completed_onboarding: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    users.push(newUser);
    this.storeUsers(users);

    // Debug logging for account creation
    console.log(`✅ Account created successfully for: ${userData.email}`);
    console.log(`👤 Total users in storage: ${users.length}`);
    console.log(`💾 User stored with ID: ${newUser.id}`);

    const tokens = {
      access_token: this.generateToken(),
      refresh_token: this.generateToken(),
    };

    // Store current user session
    localStorage.setItem(this.CURRENT_USER_KEY, JSON.stringify({
      user: this.convertToUser(newUser),
      ...tokens
    }));

    console.log(`🔑 Session tokens generated and stored for: ${userData.email}`);

    return {
      user: this.convertToUser(newUser),
      ...tokens
    };
  }

  /**
   * Mock social login function
   */
  async socialLogin(provider: 'google' | 'apple', token: string): Promise<AuthResponse> {
    await this.delay();

    // For demo purposes, create a mock social user
    const email = provider === 'google' 
      ? `google.user.${Date.now()}@gmail.com`
      : `apple.user.${Date.now()}@icloud.com`;

    const users = this.getStoredUsers();
    const existingUser = this.findUserByEmail(email);

    if (existingUser) {
      // Return existing social user
      const tokens = {
        access_token: this.generateToken(),
        refresh_token: this.generateToken(),
      };

      localStorage.setItem(this.CURRENT_USER_KEY, JSON.stringify({
        user: this.convertToUser(existingUser),
        ...tokens
      }));

      return {
        user: this.convertToUser(existingUser),
        ...tokens
      };
    } else {
      // Create new social user
      const newUser: MockUser = {
        id: (users.length + 1).toString(),
        email,
        password: 'social_auth_' + this.generateToken(),
        name: provider === 'google' ? 'Google User' : 'Apple User',
        role: 'user',
        isActive: true,
        isVerified: true,
        subscriptionTier: 'free',
        isEmailVerified: true,
        has_completed_onboarding: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      users.push(newUser);
      this.storeUsers(users);

      const tokens = {
        access_token: this.generateToken(),
        refresh_token: this.generateToken(),
      };

      localStorage.setItem(this.CURRENT_USER_KEY, JSON.stringify({
        user: this.convertToUser(newUser),
        ...tokens
      }));

      return {
        user: this.convertToUser(newUser),
        ...tokens
      };
    }
  }

  /**
   * Mock password reset request
   */
  async requestPasswordReset(email: string): Promise<void> {
    await this.delay();

    const user = this.findUserByEmail(email);
    if (!user) {
      throw new Error('User not found');
    }

    // In a real app, this would send an email
    console.log(`Password reset link sent to ${email}`);
    
    // Store reset token for demo
    localStorage.setItem(`formiq_reset_token_${email}`, this.generateToken());
  }

  /**
   * Mock password reset
   */
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await this.delay();

    // For demo purposes, just accept any token
    console.log('Password reset successful');
  }

  /**
   * Mock token validation
   */
  async validateSession(): Promise<{ data: User }> {
    await this.delay(500);

    const currentSession = localStorage.getItem(this.CURRENT_USER_KEY);
    if (!currentSession) {
      throw new Error('No active session');
    }

    const session = JSON.parse(currentSession);
    return { data: session.user };
  }

  /**
   * Mock complete onboarding
   */
  async completeOnboarding(): Promise<{ data: { user: User } }> {
    await this.delay();

    const currentSession = localStorage.getItem(this.CURRENT_USER_KEY);
    if (!currentSession) {
      throw new Error('No active session');
    }

    const session = JSON.parse(currentSession);
    const user = session.user;

    // Update user onboarding status
    const users = this.getStoredUsers();
    const userIndex = users.findIndex(u => u.id === user.id);
    if (userIndex !== -1) {
      users[userIndex].has_completed_onboarding = true;
      users[userIndex].onboarding_completed_at = new Date().toISOString();
      users[userIndex].updatedAt = new Date().toISOString();
      this.storeUsers(users);

      // Update current session
      const updatedUser = this.convertToUser(users[userIndex]);
      session.user = updatedUser;
      localStorage.setItem(this.CURRENT_USER_KEY, JSON.stringify(session));

      return { data: { user: updatedUser } };
    }

    throw new Error('User not found');
  }

  /**
   * Mock logout
   */
  async logout(): Promise<void> {
    localStorage.removeItem(this.CURRENT_USER_KEY);
  }

  /**
   * Debug method to list all stored users (for development)
   */
  getAllUsers(): MockUser[] {
    return this.getStoredUsers();
  }

  /**
   * Debug method to check if user exists
   */
  userExists(email: string): boolean {
    return !!this.findUserByEmail(email);
  }

  /**
   * Debug method to clear all users (for testing)
   */
  clearAllUsers(): void {
    localStorage.removeItem(this.STORAGE_KEY);
    localStorage.removeItem(this.CURRENT_USER_KEY);
    this.initializeDefaultUsers();
  }

  /**
   * Check if we should use mock service (when backend is not available)
   */
  static shouldUseMock(): boolean {
    // Use mock service in development or when REACT_APP_USE_MOCK_AUTH is set
    return process.env.NODE_ENV === 'development' || 
           process.env.REACT_APP_USE_MOCK_AUTH === 'true' ||
           !process.env.REACT_APP_API_URL;
  }
}

export const mockAuthService = new MockAuthService();

// Expose debugging methods globally in development
if (process.env.NODE_ENV === 'development') {
  (window as any).mockAuth = {
    getAllUsers: () => mockAuthService.getAllUsers(),
    userExists: (email: string) => mockAuthService.userExists(email),
    clearAllUsers: () => mockAuthService.clearAllUsers(),
    createTestUser: async (email: string, password: string = 'password123') => {
      try {
        const result = await mockAuthService.register({
          email,
          password,
          confirm_password: password,
          first_name: 'Test',
          last_name: 'User'
        });
        console.log('Test user created:', result);
        return result;
      } catch (error) {
        console.error('Failed to create test user:', error);
        throw error;
      }
    },
    testLogin: async (email: string, password: string = 'password123') => {
      try {
        const result = await mockAuthService.login(email, password);
        console.log('Test login successful:', result);
        return result;
      } catch (error) {
        console.error('Test login failed:', error);
        throw error;
      }
    }
  };
  
  console.log('🔧 Mock auth debugging tools available:');
  console.log('- window.mockAuth.getAllUsers() - List all users');
  console.log('- window.mockAuth.userExists(email) - Check if user exists');
  console.log('- window.mockAuth.clearAllUsers() - Clear all users');
  console.log('- window.mockAuth.createTestUser(email, password) - Create test user');
  console.log('- window.mockAuth.testLogin(email, password) - Test login');
}