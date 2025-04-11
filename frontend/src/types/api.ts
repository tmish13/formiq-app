export interface ApiResponse<T = any> {
  data: T;
  status: number;
  message?: string;
  metadata?: {
    timestamp: string;
    requestId: string;
    [key: string]: unknown;
  };
}

export interface ApiError {
  name: string;
  status: number;
  message: string;
  data?: unknown;
  code?: string;
  timestamp?: string;
}

export interface ErrorResponse {
  message: string;
  errors?: string[];
  code?: string;
}

export interface PaginationMetadata {
  timestamp: string;
  requestId: string;
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
  [key: string]: unknown;
}

export interface PaginatedResponse<T> extends Omit<ApiResponse<T>, 'metadata'> {
  metadata: PaginationMetadata;
}

export interface QueryParams {
  [key: string]: string | number | boolean | undefined;
} 