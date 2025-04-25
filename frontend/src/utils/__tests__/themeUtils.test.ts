import { getThemeValue, fallbacks } from '../../../src/utils/themeUtils';
import { Theme } from '../../../src/types/theme';

describe('themeUtils', () => {
  describe('getThemeValue', () => {
    const mockTheme: Partial<Theme> = {
      colors: {
        primary: '#123456',
        primaryDark: '#000000',
        secondary: '#654321',
        success: '#00ff00',
        successLight: '#66ff66',
        warning: '#ffff00',
        warningLight: '#ffff66',
        error: '#ff0000',
        errorLight: '#ff6666',
        background: '#ffffff',
        surface: '#f5f5f5',
        text: '#000000',
        textSecondary: '#666666',
        border: '#cccccc',
        disabled: '#999999'
      },
      typography: {
        fontFamily: 'Roboto, sans-serif',
        fontSize: {
          xs: '12px',
          sm: '14px',
          md: '16px',
          lg: '18px',
          xl: '20px'
        },
        fontWeight: {
          regular: 400,
          medium: 500,
          bold: 700
        }
      },
      transitions: {
        fast: '150ms',
        medium: '300ms',
        slow: '500ms'
      }
    };

    it('should return theme value for valid path', () => {
      expect(getThemeValue(mockTheme, 'colors.primary', '#ffffff')).toBe('#123456');
      expect(getThemeValue(mockTheme, 'colors.secondary', '#ffffff')).toBe('#654321');
      expect(getThemeValue(mockTheme, 'typography.fontSize.md', '12px')).toBe('16px');
    });

    it('should return fallback for invalid path', () => {
      expect(getThemeValue(mockTheme, 'colors.nonexistent' as any, '#ffffff')).toBe('#ffffff');
      expect(getThemeValue(mockTheme, 'typography.fontSize.xxl' as any, '24px')).toBe('24px');
    });

    it('should return fallback for undefined theme', () => {
      expect(getThemeValue(undefined, 'colors.primary', '#ffffff')).toBe('#ffffff');
      expect(getThemeValue(undefined, 'typography.fontSize.md', '16px')).toBe('16px');
    });

    it('should handle nested paths correctly', () => {
      expect(getThemeValue(mockTheme, 'typography.fontSize.sm', '12px')).toBe('14px');
      expect(getThemeValue(mockTheme, 'typography.fontSize.lg', '12px')).toBe('18px');
      expect(getThemeValue(mockTheme, 'transitions.fast', '200ms')).toBe('150ms');
      expect(getThemeValue(mockTheme, 'transitions.medium', '200ms')).toBe('300ms');
    });
  });

  describe('fallbacks', () => {
    it('should have all required color values', () => {
      expect(fallbacks.colors).toEqual(expect.objectContaining({
        primary: expect.any(String),
        primaryDark: expect.any(String),
        secondary: expect.any(String),
        success: expect.any(String),
        successLight: expect.any(String),
        warning: expect.any(String),
        warningLight: expect.any(String),
        error: expect.any(String),
        errorLight: expect.any(String),
        background: expect.any(String),
        surface: expect.any(String),
        text: expect.any(String),
        textSecondary: expect.any(String),
        border: expect.any(String),
        disabled: expect.any(String)
      }));
    });

    it('should have all required typography values', () => {
      expect(fallbacks.typography).toEqual(expect.objectContaining({
        fontFamily: expect.any(String),
        fontSize: expect.objectContaining({
          xs: expect.any(String),
          sm: expect.any(String),
          md: expect.any(String),
          lg: expect.any(String),
          xl: expect.any(String)
        }),
        fontWeight: expect.objectContaining({
          regular: expect.any(Number),
          medium: expect.any(Number),
          bold: expect.any(Number)
        })
      }));
    });

    it('should have all required spacing values', () => {
      expect(fallbacks.spacing).toEqual(expect.objectContaining({
        xs: expect.any(String),
        sm: expect.any(String),
        md: expect.any(String),
        lg: expect.any(String),
        xl: expect.any(String)
      }));
    });

    it('should have all required border radius values', () => {
      expect(fallbacks.borderRadius).toEqual({
        sm: "4px",
        md: "8px",
        lg: "12px"
      });
    });

    it('should have all required shadow values', () => {
      expect(fallbacks.shadows).toEqual(expect.objectContaining({
        sm: expect.any(String),
        md: expect.any(String),
        lg: expect.any(String)
      }));
    });

    it('should have all required transition values', () => {
      expect(fallbacks.transitions).toEqual(expect.objectContaining({
        fast: expect.any(String),
        medium: expect.any(String),
        slow: expect.any(String)
      }));
    });
  });
}); 