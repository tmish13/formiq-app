import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { App } from './App';
import * as serviceWorkerRegistration from './serviceWorkerRegistration';

// Initialize required polyfills
import './polyfills';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Failed to find the root element');
}

const root = ReactDOM.createRoot(rootElement);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://cra.link/PWA
serviceWorkerRegistration.register(); 