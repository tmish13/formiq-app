import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { App } from './App';
import { ThemeProvider } from './ThemeProvider';
import { GlobalStyles } from './styles/globalStyles';
import * as serviceWorkerRegistration from './serviceWorkerRegistration';

console.log('Starting index.tsx execution');

// Skip MSW setup and any other preparatory steps
console.log('Skipping all preparation steps - direct rendering');

try {
  const rootElement = document.getElementById('root');
  if (!rootElement) {
    throw new Error("Couldn't find root element");
  }
  
  console.log('Creating React root');
  const root = ReactDOM.createRoot(rootElement as HTMLElement);
  
  console.log('Rendering minimal React app without StrictMode');
  // Render without StrictMode to avoid double rendering/mounting
  root.render(
    <ThemeProvider>
      <GlobalStyles />
      <App />
    </ThemeProvider>
  );
  
  console.log('React app rendered successfully');
} catch (renderError) {
  console.error('Critical error during app rendering:', renderError);
  
  // Display a fallback error UI
  try {
    const errorDiv = document.createElement('div');
    errorDiv.style.position = 'fixed';
    errorDiv.style.top = '0';
    errorDiv.style.left = '0';
    errorDiv.style.width = '100%';
    errorDiv.style.height = '100%';
    errorDiv.style.backgroundColor = 'white';
    errorDiv.style.display = 'flex';
    errorDiv.style.flexDirection = 'column';
    errorDiv.style.alignItems = 'center';
    errorDiv.style.justifyContent = 'center';
    errorDiv.style.padding = '20px';
    errorDiv.style.color = '#333';
    errorDiv.style.fontFamily = 'system-ui, sans-serif';
    errorDiv.style.zIndex = '9999';
    
    const title = document.createElement('h1');
    title.textContent = 'App Error';
    title.style.color = 'red';
    title.style.marginBottom = '15px';
    
    const message = document.createElement('p');
    message.textContent = renderError instanceof Error 
      ? renderError.message 
      : 'Unknown error occurred';
    
    errorDiv.appendChild(title);
    errorDiv.appendChild(message);
    
    const body = document.body;
    // Clear body first
    while (body.firstChild) {
      body.removeChild(body.firstChild);
    }
    body.appendChild(errorDiv);
  } catch (fallbackError) {
    console.error('Failed to show error UI:', fallbackError);
  }
} 