/**
 * Services index file
 * Centralizes service exports for easier imports
 * Import services directly from their modules to avoid naming conflicts
 */

// API Services
export * from './api/handlers';

// Feature Services
export * from './formCheckService';
export * from './workoutService';
export * from './progressService';
export * from './exerciseLibraryService';
export * from './socialService';
export * from './videoService';
export * from './healthService';
export * from './exerciseConfigService';

// Auth Services
export * from './auth';
export * from './sessionService';

// Infrastructure Services
export * from './errorHandlingService';
export * from './syncService';
export * from './storageService'; 