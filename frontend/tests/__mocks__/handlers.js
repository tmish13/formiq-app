import { rest } from 'msw';

export const handlers = [
  rest.get('/api/form-analysis/history', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        data: []
      })
    );
  }),
  
  rest.post('/api/form-analysis', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        message: 'Analysis saved successfully'
      })
    );
  })
]; 