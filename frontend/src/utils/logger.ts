export const logError = (message: string, error: unknown): void => {
  console.error(`[ERROR] ${message}:`, error);
  // In a production environment, you might want to send this to a logging service
  // like Sentry, LogRocket, etc.
}; 