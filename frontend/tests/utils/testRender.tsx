import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { mockThemeWithFallbacks } from '../__mocks__/mockTheme';
import { Provider } from 'react-redux';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { store } from '../../src/store';
import userEvent from '@testing-library/user-event';

// For any components that need providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialRoute?: string;
  useMemoryRouter?: boolean;
  routePath?: string;
  initialReduxState?: any;
  withoutTheme?: boolean;
  withoutRouter?: boolean;
  withoutRedux?: boolean;
}

/**
 * Custom render function that wraps components with all necessary providers
 * (ThemeProvider, Redux Provider, Router) by default
 */
export function testRender(
  ui: ReactElement,
  {
    initialRoute = '/',
    useMemoryRouter = false,
    routePath,
    initialReduxState,
    withoutTheme = false,
    withoutRouter = false,
    withoutRedux = false,
    ...renderOptions
  }: CustomRenderOptions = {}
) {
  const Wrapper = ({ children }: { children: React.ReactNode }) => {
    // Component tree from inside to outside
    let wrappedChildren = children;

    // Wrap with route if path is provided
    if (routePath && useMemoryRouter) {
      wrappedChildren = (
        <Routes>
          <Route path={routePath} element={<>{wrappedChildren}</>} />
        </Routes>
      );
    }

    // Wrap with router if needed
    if (!withoutRouter) {
      const Router = useMemoryRouter ? MemoryRouter : BrowserRouter;
      wrappedChildren = (
        <Router initialEntries={useMemoryRouter ? [initialRoute] : undefined}>
          {wrappedChildren}
        </Router>
      );
    }

    // Wrap with Redux if needed
    if (!withoutRedux) {
      // Can customize this to create a store with initial state if needed
      const testStore = initialReduxState ? 
        // Add logic here to create store with initial state
        store : store;
        
      wrappedChildren = (
        <Provider store={testStore}>
          {wrappedChildren}
        </Provider>
      );
    }

    // Wrap with theme if needed
    if (!withoutTheme) {
      wrappedChildren = (
        <ThemeProvider theme={mockThemeWithFallbacks}>
          {wrappedChildren}
        </ThemeProvider>
      );
    }

    return <>{wrappedChildren}</>;
  };

  const result = render(ui, { wrapper: Wrapper, ...renderOptions });
  
  return {
    ...result,
    user: userEvent.setup(),
  };
}

// Re-export everything from testing-library
export * from '@testing-library/react';
export { testRender as render }; 