import { AxiosRequestConfig } from 'axios';

/**
 * Generates a URL string based on provided request options
 * @param options The Axios request options
 * @param baseUrl Base URL to use (optional)
 * @returns A constructed URL string
 */
export function getUrlByRequestOptions(options: AxiosRequestConfig, baseUrl: string = process.env.REACT_APP_API_URL || '/api'): string {
  if (!options.url) {
    return baseUrl;
  }

  // If the URL is already absolute, return it
  if (options.url.startsWith('http://') || options.url.startsWith('https://')) {
    return options.url;
  }

  // Ensure the base URL doesn't end with a slash and the path doesn't start with one
  const normalizedBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  const normalizedPath = options.url.startsWith('/') ? options.url : `/${options.url}`;

  // Construct URL
  let url = `${normalizedBaseUrl}${normalizedPath}`;

  // Add query parameters if they exist
  if (options.params) {
    const queryString = Object.entries(options.params)
      .filter(([_, value]) => value !== undefined && value !== null)
      .map(([key, value]) => {
        if (Array.isArray(value)) {
          return value
            .map(v => `${encodeURIComponent(key)}=${encodeURIComponent(String(v))}`)
            .join('&');
        }
        return `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`;
      })
      .join('&');

    if (queryString) {
      url += `?${queryString}`;
    }
  }

  return url;
}

export default getUrlByRequestOptions; 