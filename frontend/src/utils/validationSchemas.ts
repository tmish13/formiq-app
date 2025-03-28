import * as yup from 'yup';

export const loginSchema = yup.object().shape({
  email: yup
    .string()
    .email('Please enter a valid email address')
    .required('Email is required'),
  password: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .required('Password is required'),
});

export const registerSchema = yup.object().shape({
  email: yup
    .string()
    .email('Please enter a valid email address')
    .required('Email is required'),
  password: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'Password must contain at least one uppercase letter, one lowercase letter, and one number'
    )
    .required('Password is required'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password')], 'Passwords must match')
    .required('Please confirm your password'),
  firstName: yup.string().required('First name is required'),
  lastName: yup.string().required('Last name is required'),
});

export const workoutSchema = yup.object().shape({
  name: yup.string().required('Workout name is required'),
  description: yup.string(),
  exercises: yup.array().of(
    yup.object().shape({
      name: yup.string().required('Exercise name is required'),
      sets: yup.number().min(1, 'Must have at least 1 set').required('Number of sets is required'),
      reps: yup.number().min(1, 'Must have at least 1 rep').required('Number of reps is required'),
    })
  ),
}); 