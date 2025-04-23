import { createElement } from 'react';
import type { Location, NavigateFunction, Params } from 'react-router-dom';

interface RouterProps {
  children?: React.ReactNode;
  initialEntries?: string[];
}

interface RouteProps {
  path?: string;
  element?: React.ReactNode;
}

interface NavigateProps {
  to: string;
  replace?: boolean;
}

export const MemoryRouter = ({ children }: RouterProps) => createElement('div', null, children);
export const BrowserRouter = ({ children }: RouterProps) => createElement('div', null, children);
export const Route = ({ element }: RouteProps) => createElement('div', null, element);
export const Routes = ({ children }: { children?: React.ReactNode }) => createElement('div', null, children);
export const Navigate = ({ to }: NavigateProps) => createElement('div', { 'data-testid': 'navigate', to });

export const useLocation = jest.fn<Location, []>(() => ({
  pathname: '/',
  search: '',
  hash: '',
  state: null,
  key: 'default',
}));

export const useNavigate = jest.fn<NavigateFunction, []>(() => jest.fn());
export const useParams = jest.fn<Params<string>, []>(() => ({}));
export const useSearchParams = jest.fn(() => [new URLSearchParams(), jest.fn()]);

export const Link = ({ to, children }: { to: string; children?: React.ReactNode }) =>
  createElement('a', { href: to }, children);

export const NavLink = Link;

export const Outlet = () => createElement('div', { 'data-testid': 'outlet' });

export const useOutletContext = jest.fn();
export const useHref = jest.fn((to: string) => to);

// Additional exports for React Router v6 that might be used
export const createMemoryRouter = jest.fn(() => ({
  navigate: jest.fn(),
  state: {
    location: {
      pathname: '/',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    },
    matches: [],
    loaderData: {},
  }
}));

export const createBrowserRouter = jest.fn(createMemoryRouter);
export const RouterProvider = ({ router, children }: { router: any; children?: React.ReactNode }) => 
  createElement('div', null, children);

// More hooks from React Router v6
export const useMatch = jest.fn(() => ({
  params: {},
  pathname: '/',
  pathnameBase: '/',
  pattern: {
    path: '/',
    caseSensitive: false,
    end: true
  }
}));

export const useResolvedPath = jest.fn((to: string) => ({
  pathname: to,
  search: '',
  hash: ''
}));

export const useRoutes = jest.fn(() => null);
export const useMatches = jest.fn(() => []);

// Handle redirect
export const Redirect = ({ to }: { to: string }) => createElement('div', { 'data-testid': 'redirect', to });

// Custom hook exports that might be added by the app
export const useAuth = jest.fn();

// Re-export to handle destructured imports
export default {
  MemoryRouter,
  BrowserRouter,
  Route,
  Routes,
  Navigate,
  useLocation,
  useNavigate,
  useParams,
  Link,
  NavLink,
  Outlet,
  useOutletContext,
  useHref,
  useMatch,
  useResolvedPath,
  useRoutes,
  useSearchParams,
  createMemoryRouter,
  createBrowserRouter,
  RouterProvider,
  Redirect
}; 