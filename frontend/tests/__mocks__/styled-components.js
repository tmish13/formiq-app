import React from 'react';
import { mockThemeWithFallbacks } from './mockTheme';

// Create a styled mock helper
const styled = (Component) => {
  return (strings, ...expressions) => {
    // Return a functional component that passes props to the base Component
    const StyledComponent = React.forwardRef((props, ref) => {
      return <Component ref={ref} {...props} data-testid={props['data-testid']} />;
    });
    StyledComponent.displayName = `Styled(${Component.displayName || Component.name || 'Component'})`;
    // Add attrs method to support .attrs functionality
    StyledComponent.attrs = (attrs) => {
      return styled(Component)(strings, ...expressions);
    };
    return StyledComponent;
  };
};

// Add styled.[tag] methods for all HTML elements
const tags = [
  'a', 'abbr', 'address', 'area', 'article', 'aside', 'audio', 'b', 'base', 'bdi', 'bdo', 'big', 'blockquote', 'body',
  'br', 'button', 'canvas', 'caption', 'center', 'cite', 'code', 'col', 'colgroup', 'data', 'datalist', 'dd', 'del', 
  'details', 'dfn', 'dialog', 'div', 'dl', 'dt', 'em', 'embed', 'fieldset', 'figcaption', 'figure', 'footer', 'form',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'header', 'hgroup', 'hr', 'html', 'i', 'iframe', 'img', 'input', 'ins',
  'kbd', 'keygen', 'label', 'legend', 'li', 'link', 'main', 'map', 'mark', 'menu', 'menuitem', 'meta', 'meter', 'nav',
  'noscript', 'object', 'ol', 'optgroup', 'option', 'output', 'p', 'param', 'picture', 'pre', 'progress', 'q', 'rp',
  'rt', 'ruby', 's', 'samp', 'script', 'section', 'select', 'small', 'source', 'span', 'strong', 'style', 'sub', 'summary',
  'sup', 'table', 'tbody', 'td', 'textarea', 'tfoot', 'th', 'thead', 'time', 'title', 'tr', 'track', 'u', 'ul', 'var',
  'video', 'wbr'
];

tags.forEach(tag => {
  styled[tag] = styled(tag);
});

// Mock the ThemeProvider component
const ThemeProvider = ({ theme = mockThemeWithFallbacks, children }) => {
  return <div data-testid="styled-components-theme-provider">{children}</div>;
};

// Mock other styled-components exports
const css = (...args) => ({});
const keyframes = (...args) => 'animation-name';
const createGlobalStyle = (...args) => {
  const GlobalStyle = () => null;
  return GlobalStyle;
};
const ServerStyleSheet = class {
  collectStyles = jest.fn(children => children);
  getStyleElement = jest.fn(() => []);
  getStyleTags = jest.fn(() => '');
  seal = jest.fn();
};

// Core styled-components functions and components
styled.div = styled('div');
styled.createGlobalStyle = createGlobalStyle;

// Export all mocked components and functions
module.exports = {
  __esModule: true,
  default: styled,
  styled,
  css,
  keyframes,
  createGlobalStyle,
  ThemeProvider,
  ServerStyleSheet,
  // Support for "as" prop and other styled API methods
  isStyledComponent: true,
}; 