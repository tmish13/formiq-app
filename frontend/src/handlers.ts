import { rest } from 'msw';

// Define handlers array
export const handlers = [
  // Add your mock API handlers here
  rest.get('/api/test', (req, res, ctx) => {
    return res(ctx.json({ message: 'Test successful' }));
  }),
]; 