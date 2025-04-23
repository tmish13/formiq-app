import React, { PropsWithChildren } from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '../../src/theme';
import rootReducer from '../../src/store/rootReducer';

interface TestWrapperProps {
  initialState?: Record<string, any>;
}

export const createTestWrapper = ({ initialState = {} }: TestWrapperProps = {}) => {
  const store = configureStore({
    reducer: rootReducer,
    preloadedState: initialState,
  });

  return ({ children }: PropsWithChildren<{}>) => (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </ThemeProvider>
    </Provider>
  );
};

export const renderWithProviders = (
  ui: React.ReactElement,
  options: RenderOptions & TestWrapperProps = {}
): RenderResult => {
  const { initialState, ...renderOptions } = options;
  const TestWrapper = createTestWrapper({ initialState });
  return render(ui, { wrapper: TestWrapper, ...renderOptions });
}; 