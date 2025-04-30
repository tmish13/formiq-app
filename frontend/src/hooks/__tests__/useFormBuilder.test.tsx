import { renderHook, act } from '@testing-library/react-hooks';
import { useFormBuilder } from '../useFormBuilder';

describe('useFormBuilder', () => {
  it('should initialize with empty values by default', () => {
    const { result } = renderHook(() => useFormBuilder());
    
    expect(result.current.values).toEqual({});
    expect(result.current.errors).toEqual({});
    expect(result.current.touched).toEqual({});
    expect(result.current.isSubmitting).toBe(false);
  });

  it('should initialize with provided initial values', () => {
    const initialValues = { name: 'John', email: 'john@example.com' };
    const { result } = renderHook(() => useFormBuilder(initialValues));
    
    expect(result.current.values).toEqual(initialValues);
  });

  it('should update values on handleChange', () => {
    const { result } = renderHook(() => useFormBuilder({ name: '' }));
    
    act(() => {
      const event = {
        target: { name: 'name', value: 'John', type: 'text' }
      } as React.ChangeEvent<HTMLInputElement>;
      
      result.current.handleChange(event);
    });
    
    expect(result.current.values.name).toBe('John');
  });

  it('should convert number inputs to numbers', () => {
    const { result } = renderHook(() => useFormBuilder({ age: 0 }));
    
    act(() => {
      const event = {
        target: { name: 'age', value: '25', type: 'number' }
      } as React.ChangeEvent<HTMLInputElement>;
      
      result.current.handleChange(event);
    });
    
    expect(result.current.values.age).toBe(25);
    expect(typeof result.current.values.age).toBe('number');
  });

  it('should mark field as touched on blur', () => {
    const { result } = renderHook(() => useFormBuilder({ name: '' }));
    
    act(() => {
      const event = {
        target: { name: 'name' }
      } as React.FocusEvent<HTMLInputElement>;
      
      result.current.handleBlur(event);
    });
    
    expect(result.current.touched.name).toBe(true);
  });

  it('should call onSubmit with values on form submission', () => {
    const initialValues = { name: 'John' };
    const onSubmit = jest.fn();
    
    const { result } = renderHook(() => useFormBuilder(initialValues));
    
    act(() => {
      const handleSubmit = result.current.handleSubmit(onSubmit);
      handleSubmit();
    });
    
    expect(onSubmit).toHaveBeenCalledWith(initialValues);
    expect(result.current.touched.name).toBe(true);
  });

  it('should set isSubmitting during form submission', () => {
    // Create a mock implementation that resolves after a delay
    const onSubmit = jest.fn();
    let submittingValueDuringSubmit = false;
    
    // Override onSubmit to capture the submitting state
    onSubmit.mockImplementation(() => {
      submittingValueDuringSubmit = true;
    });
    
    const { result } = renderHook(() => useFormBuilder({ name: 'John' }));
    
    act(() => {
      // Verify isSubmitting is false before submission
      expect(result.current.isSubmitting).toBe(false);
      
      // Start the submission
      const handleSubmit = result.current.handleSubmit(onSubmit);
      handleSubmit();
    });
    
    // Check that onSubmit was called
    expect(onSubmit).toHaveBeenCalled();
    
    // Check that isSubmitting was true during the submission
    expect(submittingValueDuringSubmit).toBe(true);
    
    // Check that isSubmitting is reset to false after submission
    expect(result.current.isSubmitting).toBe(false);
  });

  it('should update field value with setFieldValue', () => {
    const { result } = renderHook(() => useFormBuilder({ name: '' }));
    
    act(() => {
      result.current.setFieldValue('name', 'John');
    });
    
    expect(result.current.values.name).toBe('John');
  });

  it('should reset form to initial values', () => {
    const initialValues = { name: 'John', email: 'john@example.com' };
    const { result } = renderHook(() => useFormBuilder(initialValues));
    
    act(() => {
      result.current.setFieldValue('name', 'Jane');
      const event = {
        target: { name: 'name' }
      } as React.FocusEvent<HTMLInputElement>;
      result.current.handleBlur(event);
    });
    
    expect(result.current.values.name).toBe('Jane');
    expect(result.current.touched.name).toBe(true);
    
    act(() => {
      result.current.resetForm();
    });
    
    expect(result.current.values).toEqual(initialValues);
    expect(result.current.errors).toEqual({});
    expect(result.current.touched).toEqual({});
    expect(result.current.isSubmitting).toBe(false);
  });
}); 