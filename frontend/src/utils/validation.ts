import * as yup from 'yup';

// Registration validation schema
export const registrationSchema = yup.object().shape({
  email: yup
    .string()
    .email('Please enter a valid email')
    .required('Email is required'),
  password: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .matches(/[0-9]/, 'Password must contain at least one number')
    .matches(/[a-z]/, 'Password must contain at least one lowercase letter')
    .matches(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .matches(/[^\w]/, 'Password must contain at least one symbol')
    .required('Password is required'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password')], 'Passwords must match')
    .required('Please confirm your password'),
  username: yup
    .string()
    .min(3, 'Username must be at least 3 characters')
    .max(30, 'Username must be less than 30 characters')
    .matches(/^[a-zA-Z0-9_-]+$/, 'Username can only contain letters, numbers, underscores and dashes')
    .required('Username is required'),
});

// Login validation schema
export const loginSchema = yup.object().shape({
  email: yup
    .string()
    .email('Please enter a valid email')
    .required('Email is required'),
  password: yup
    .string()
    .required('Password is required'),
});

interface VideoFile extends File {
  size: number;
  type: string;
}

// Video upload validation schema
export const videoUploadSchema = yup.object().shape({
  file: yup
    .mixed<VideoFile>()
    .required('Please select a video file')
    .test('fileSize', 'File size is too large', (value?: VideoFile) => {
      if (!value) return false;
      const maxSize = parseInt(process.env.REACT_APP_MAX_VIDEO_SIZE || '100000000', 10); // 100MB default
      return value.size <= maxSize;
    })
    .test('fileType', 'Unsupported file type', (value?: VideoFile) => {
      if (!value) return false;
      const allowedTypes = (process.env.REACT_APP_ALLOWED_VIDEO_TYPES || 'mp4,webm,mov').split(',');
      const fileType = value.type.split('/')[1];
      return allowedTypes.includes(fileType);
    }),
  title: yup
    .string()
    .min(3, 'Title must be at least 3 characters')
    .max(100, 'Title must be less than 100 characters')
    .required('Please enter a title for your video'),
  description: yup
    .string()
    .max(500, 'Description must be less than 500 characters'),
  exerciseType: yup
    .string()
    .required('Please select an exercise type'),
});

// Profile update validation schema
export const profileUpdateSchema = yup.object().shape({
  username: yup
    .string()
    .min(3, 'Username must be at least 3 characters')
    .max(30, 'Username must be less than 30 characters')
    .matches(/^[a-zA-Z0-9_-]+$/, 'Username can only contain letters, numbers, underscores and dashes'),
  email: yup
    .string()
    .email('Please enter a valid email'),
  fullName: yup
    .string()
    .max(100, 'Full name must be less than 100 characters'),
  bio: yup
    .string()
    .max(500, 'Bio must be less than 500 characters'),
  preferences: yup.object().shape({
    emailNotifications: yup.boolean(),
    pushNotifications: yup.boolean(),
    theme: yup.string().oneOf(['light', 'dark', 'system']),
    language: yup.string().length(2),
  }),
});

// Password update validation schema
export const passwordUpdateSchema = yup.object().shape({
  currentPassword: yup
    .string()
    .required('Current password is required'),
  newPassword: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .matches(/[0-9]/, 'Password must contain at least one number')
    .matches(/[a-z]/, 'Password must contain at least one lowercase letter')
    .matches(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .matches(/[^\w]/, 'Password must contain at least one symbol')
    .required('New password is required'),
  confirmNewPassword: yup
    .string()
    .oneOf([yup.ref('newPassword')], 'Passwords must match')
    .required('Please confirm your new password'),
}); 