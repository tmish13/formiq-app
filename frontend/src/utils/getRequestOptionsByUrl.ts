import { AxiosRequestConfig } from 'axios';

/**
 * Returns request options based on URL patterns
 * @param url The URL to get options for
 * @returns Axios request options
 */
export function getRequestOptionsByUrl(url: string | undefined): AxiosRequestConfig {
  // Default options
  const defaultOptions: AxiosRequestConfig = {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 seconds
  };

  // If URL is not a string, return default options
  if (typeof url !== 'string') {
    return defaultOptions;
  }

  // For form uploads
  if (url.includes('upload') || url.includes('avatar')) {
    return {
      ...defaultOptions,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 seconds for uploads
    };
  }

  // For downloading files
  if (url.includes('export') || url.includes('download')) {
    return {
      ...defaultOptions,
      responseType: 'blob',
    };
  }

  return defaultOptions;
}

export default getRequestOptionsByUrl; 