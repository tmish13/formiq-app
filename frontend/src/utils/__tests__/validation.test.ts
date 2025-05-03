import {
  registrationSchema,
  loginSchema,
  videoUploadSchema,
  profileUpdateSchema,
  passwordUpdateSchema
} from '../validation';

describe('Validation Schemas', () => {
  describe('Registration Schema', () => {
    it('should validate valid registration data', async () => {
      const validData = {
        email: 'test@example.com',
        password: 'Password123!',
        confirmPassword: 'Password123!',
        username: 'testuser'
      };
      
      await expect(registrationSchema.validate(validData)).resolves.toEqual(validData);
    });
    
    it('should reject invalid email format', async () => {
      const invalidData = {
        email: 'invalid-email',
        password: 'Password123!',
        confirmPassword: 'Password123!',
        username: 'testuser'
      };
      
      await expect(registrationSchema.validate(invalidData)).rejects.toThrow(/valid email/);
    });
    
    it('should reject weak passwords', async () => {
      // Test each password requirement one at a time
      const testCases = [
        // First, a password that's too short
        { 
          password: 'short', 
          error: /at least 8 characters/ 
        },
        // Then, test a longer password that meets length but fails the next requirement (numbers)
        { 
          password: 'onlylowercase', 
          error: /must contain at least one number/ 
        },
        // Then a password with lowercase and numbers but no uppercase
        { 
          password: 'onlylowercase123', 
          error: /must contain at least one uppercase/ 
        },
        // Then a password with lowercase, numbers, and uppercase but no symbols
        { 
          password: 'WithUpperAndNumbers123', 
          error: /must contain at least one symbol/ 
        }
      ];
      
      for (const testCase of testCases) {
        const invalidData = {
          email: 'test@example.com',
          password: testCase.password,
          confirmPassword: testCase.password,
          username: 'testuser'
        };
        
        await expect(registrationSchema.validate(invalidData)).rejects.toThrow(testCase.error);
      }
    });
    
    it('should reject when passwords do not match', async () => {
      const invalidData = {
        email: 'test@example.com',
        password: 'Password123!',
        confirmPassword: 'DifferentPassword123!',
        username: 'testuser'
      };
      
      await expect(registrationSchema.validate(invalidData)).rejects.toThrow(/Passwords must match/);
    });
    
    it('should reject invalid usernames', async () => {
      const testCases = [
        { username: 'a', error: /at least 3 characters/ },
        { username: 'a'.repeat(31), error: /less than 30 characters/ },
        { username: 'invalid@username', error: /can only contain/ }
      ];
      
      for (const testCase of testCases) {
        const invalidData = {
          email: 'test@example.com',
          password: 'Password123!',
          confirmPassword: 'Password123!',
          username: testCase.username
        };
        
        await expect(registrationSchema.validate(invalidData)).rejects.toThrow(testCase.error);
      }
    });
  });
  
  describe('Login Schema', () => {
    it('should validate valid login data', async () => {
      const validData = {
        email: 'test@example.com',
        password: 'Password123!'
      };
      
      await expect(loginSchema.validate(validData)).resolves.toEqual(validData);
    });
    
    it('should reject missing email', async () => {
      const invalidData = {
        email: '',
        password: 'Password123!'
      };
      
      await expect(loginSchema.validate(invalidData)).rejects.toThrow(/Email is required/);
    });
    
    it('should reject missing password', async () => {
      const invalidData = {
        email: 'test@example.com',
        password: ''
      };
      
      await expect(loginSchema.validate(invalidData)).rejects.toThrow(/Password is required/);
    });
    
    it('should reject invalid email format', async () => {
      const invalidData = {
        email: 'invalid-email',
        password: 'Password123!'
      };
      
      await expect(loginSchema.validate(invalidData)).rejects.toThrow(/valid email/);
    });
  });
  
  describe('Video Upload Schema', () => {
    let originalEnv: NodeJS.ProcessEnv;
    
    beforeEach(() => {
      originalEnv = process.env;
      process.env = {
        ...originalEnv,
        REACT_APP_MAX_VIDEO_SIZE: '10000000', // 10MB
        REACT_APP_ALLOWED_VIDEO_TYPES: 'mp4,webm,mov'
      };
    });
    
    afterEach(() => {
      process.env = originalEnv;
    });
    
    it('should validate valid video upload data', async () => {
      const validFile = {
        size: 1000000, // 1MB
        type: 'video/mp4'
      } as File;
      
      const validData = {
        file: validFile,
        title: 'Test Video',
        description: 'Test description',
        exerciseType: 'squats'
      };
      
      await expect(videoUploadSchema.validate(validData)).resolves.toEqual(validData);
    });
    
    it('should reject large files', async () => {
      const largeFile = {
        size: 20000000, // 20MB (exceeds the 10MB limit)
        type: 'video/mp4'
      } as File;
      
      const invalidData = {
        file: largeFile,
        title: 'Test Video',
        description: 'Test description',
        exerciseType: 'squats'
      };
      
      await expect(videoUploadSchema.validate(invalidData)).rejects.toThrow(/File size is too large/);
    });
    
    it('should reject unsupported file types', async () => {
      const invalidFile = {
        size: 1000000,
        type: 'video/avi' // Not in the allowed types
      } as File;
      
      const invalidData = {
        file: invalidFile,
        title: 'Test Video',
        description: 'Test description',
        exerciseType: 'squats'
      };
      
      await expect(videoUploadSchema.validate(invalidData)).rejects.toThrow(/Unsupported file type/);
    });
    
    it('should reject missing title', async () => {
      const validFile = {
        size: 1000000,
        type: 'video/mp4'
      } as File;
      
      const invalidData = {
        file: validFile,
        title: '',
        description: 'Test description',
        exerciseType: 'squats'
      };
      
      await expect(videoUploadSchema.validate(invalidData)).rejects.toThrow(/at least 3 characters/);
    });
  });
  
  describe('Profile Update Schema', () => {
    it('should validate valid profile update data', async () => {
      const validData = {
        username: 'updateduser',
        email: 'updated@example.com',
        fullName: 'Updated User',
        bio: 'This is my updated bio',
        preferences: {
          emailNotifications: true,
          pushNotifications: false,
          theme: 'dark',
          language: 'en'
        }
      };
      
      await expect(profileUpdateSchema.validate(validData)).resolves.toEqual(validData);
    });
    
    it('should reject invalid email format', async () => {
      const invalidData = {
        username: 'updateduser',
        email: 'invalid-email',
        fullName: 'Updated User',
        bio: 'This is my updated bio',
        preferences: {
          emailNotifications: true,
          pushNotifications: false,
          theme: 'dark',
          language: 'en'
        }
      };
      
      await expect(profileUpdateSchema.validate(invalidData)).rejects.toThrow(/valid email/);
    });
    
    it('should reject invalid username', async () => {
      const invalidData = {
        username: 'invalid@user',
        email: 'updated@example.com',
        fullName: 'Updated User',
        bio: 'This is my updated bio',
        preferences: {
          emailNotifications: true,
          pushNotifications: false,
          theme: 'dark',
          language: 'en'
        }
      };
      
      await expect(profileUpdateSchema.validate(invalidData)).rejects.toThrow(/can only contain/);
    });
    
    it('should reject invalid theme', async () => {
      const invalidData = {
        username: 'updateduser',
        email: 'updated@example.com',
        fullName: 'Updated User',
        bio: 'This is my updated bio',
        preferences: {
          emailNotifications: true,
          pushNotifications: false,
          theme: 'invalid-theme',
          language: 'en'
        }
      };
      
      await expect(profileUpdateSchema.validate(invalidData)).rejects.toThrow();
    });
  });
  
  describe('Password Update Schema', () => {
    it('should validate valid password update data', async () => {
      const validData = {
        currentPassword: 'CurrentPassword123!',
        newPassword: 'NewPassword123!',
        confirmNewPassword: 'NewPassword123!'
      };
      
      await expect(passwordUpdateSchema.validate(validData)).resolves.toEqual(validData);
    });
    
    it('should reject when new password is too weak', async () => {
      const invalidData = {
        currentPassword: 'CurrentPassword123!',
        newPassword: 'weak',
        confirmNewPassword: 'weak'
      };
      
      await expect(passwordUpdateSchema.validate(invalidData)).rejects.toThrow(/at least 8 characters/);
    });
    
    it('should reject when passwords do not match', async () => {
      const invalidData = {
        currentPassword: 'CurrentPassword123!',
        newPassword: 'NewPassword123!',
        confirmNewPassword: 'DifferentPassword123!'
      };
      
      await expect(passwordUpdateSchema.validate(invalidData)).rejects.toThrow(/Passwords must match/);
    });
    
    it('should reject when current password is missing', async () => {
      const invalidData = {
        currentPassword: '',
        newPassword: 'NewPassword123!',
        confirmNewPassword: 'NewPassword123!'
      };
      
      await expect(passwordUpdateSchema.validate(invalidData)).rejects.toThrow(/Current password is required/);
    });
  });
}); 