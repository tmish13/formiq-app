import { faker } from '@faker-js/faker';

export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
  timestamp: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  meta: {
    currentPage: number;
    totalPages: number;
    totalItems: number;
    itemsPerPage: number;
  };
}

export const createApiResponse = <T>(data: T, status = 200): ApiResponse<T> => ({
  data,
  status,
  timestamp: new Date().toISOString(),
  ...(status >= 400 ? { message: faker.lorem.sentence() } : {}),
});

export const createPaginatedResponse = <T>(
  items: T[],
  page = 1,
  itemsPerPage = 10,
  totalItems?: number
): PaginatedResponse<T> => {
  const total = totalItems ?? faker.number.int({ min: items.length, max: 100 });
  const totalPages = Math.ceil(total / itemsPerPage);

  return {
    data: items,
    status: 200,
    timestamp: new Date().toISOString(),
    meta: {
      currentPage: page,
      totalPages,
      totalItems: total,
      itemsPerPage,
    },
  };
};

export const createErrorResponse = (
  status = 400,
  message = faker.lorem.sentence()
): ApiResponse<null> => ({
  data: null,
  status,
  message,
  timestamp: new Date().toISOString(),
}); 