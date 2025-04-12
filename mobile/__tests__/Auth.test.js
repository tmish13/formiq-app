import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import AuthService from '../src/services/AuthService';
import LoginScreen from '../src/screens/LoginScreen';
import RegisterScreen from '../src/screens/RegisterScreen';

jest.mock('@react-native-async-storage/async-storage', () => ({
  setItem: jest.fn(),
  getItem: jest.fn(),
  removeItem: jest.fn(),
}));

describe('Authentication', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Login', () => {
    it('handles successful login', async () => {
      const mockLogin = jest.fn().mockResolvedValue({
        token: 'test-token',
        user: { id: 1, email: 'test@example.com' },
      });
      
      const { getByTestId, getByText } = render(
        <LoginScreen onLogin={mockLogin} />
      );
      
      fireEvent.changeText(getByTestId('email-input'), 'test@example.com');
      fireEvent.changeText(getByTestId('password-input'), 'password123');
      fireEvent.press(getByTestId('login-button'));
      
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
        });
        expect(AsyncStorage.setItem).toHaveBeenCalledWith(
          'auth_token',
          'test-token'
        );
      });
    });

    it('handles login errors', async () => {
      const mockLogin = jest.fn().mockRejectedValue(new Error('Invalid credentials'));
      
      const { getByTestId, getByText } = render(
        <LoginScreen onLogin={mockLogin} />
      );
      
      fireEvent.changeText(getByTestId('email-input'), 'test@example.com');
      fireEvent.changeText(getByTestId('password-input'), 'wrongpass');
      fireEvent.press(getByTestId('login-button'));
      
      await waitFor(() => {
        expect(getByText('Invalid credentials')).toBeTruthy();
      });
    });
  });

  describe('Registration', () => {
    it('handles successful registration', async () => {
      const mockRegister = jest.fn().mockResolvedValue({
        token: 'test-token',
        user: { id: 1, email: 'new@example.com' },
      });
      
      const { getByTestId } = render(
        <RegisterScreen onRegister={mockRegister} />
      );
      
      fireEvent.changeText(getByTestId('email-input'), 'new@example.com');
      fireEvent.changeText(getByTestId('password-input'), 'password123');
      fireEvent.changeText(getByTestId('confirm-password-input'), 'password123');
      fireEvent.press(getByTestId('register-button'));
      
      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith({
          email: 'new@example.com',
          password: 'password123',
        });
        expect(AsyncStorage.setItem).toHaveBeenCalledWith(
          'auth_token',
          'test-token'
        );
      });
    });

    it('validates password match', async () => {
      const { getByTestId, getByText } = render(<RegisterScreen />);
      
      fireEvent.changeText(getByTestId('password-input'), 'password123');
      fireEvent.changeText(getByTestId('confirm-password-input'), 'password456');
      fireEvent.press(getByTestId('register-button'));
      
      await waitFor(() => {
        expect(getByText('Passwords do not match')).toBeTruthy();
      });
    });
  });

  describe('Session Management', () => {
    it('checks for existing session on app start', async () => {
      AsyncStorage.getItem.mockResolvedValue('existing-token');
      
      const result = await AuthService.checkSession();
      
      expect(result).toBe(true);
      expect(AsyncStorage.getItem).toHaveBeenCalledWith('auth_token');
    });

    it('handles logout', async () => {
      await AuthService.logout();
      
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('auth_token');
    });
  });
}); 