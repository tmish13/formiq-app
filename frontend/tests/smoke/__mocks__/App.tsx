import React from 'react';
import { Routes, Route } from 'react-router-dom';

// Mock routes for testing
const mockRoutes = [
  { path: '/', element: <div>Home Page</div> },
  { path: '/login', element: <div>Login Page</div> },
  { path: '/register', element: <div>Register Page</div> },
  { path: '/analyze', element: <div>Analyze Page</div> },
  { path: '/results/:id', element: <div>Results Page</div> },
  { path: '/dashboard', element: <div>Dashboard Page</div> },
];

export const App: React.FC = () => {
  return (
    <div data-testid="app">
      <Routes>
        {mockRoutes.map((route) => (
          <Route key={route.path} path={route.path} element={route.element} />
        ))}
      </Routes>
    </div>
  );
}; 