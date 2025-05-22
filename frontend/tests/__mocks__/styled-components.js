import React from 'react';

// Create a very simple mock of styled-components
const styled = {
  div: () => props => <div {...props} />,
  video: () => React.forwardRef((props, ref) => <video ref={ref} {...props} />),
  canvas: () => props => <canvas {...props} />,
  button: () => props => <button {...props} />,
  ul: () => props => <ul {...props} />,
  li: () => props => <li {...props} />,
  p: () => props => <p {...props} />,
  span: () => props => <span {...props} />,
  section: () => props => <section {...props} />,
  header: () => props => <header {...props} />,
  footer: () => props => <footer {...props} />,
  nav: () => props => <nav {...props} />,
  article: () => props => <article {...props} />,
  main: () => props => <main {...props} />,
  aside: () => props => <aside {...props} />,
  form: () => props => <form {...props} />,
  input: () => props => <input {...props} />,
  textarea: () => props => <textarea {...props} />,
  select: () => props => <select {...props} />,
  option: () => props => <option {...props} />,
  h1: () => props => <h1 {...props} />,
  h2: () => props => <h2 {...props} />,
  h3: () => props => <h3 {...props} />,
  h4: () => props => <h4 {...props} />,
  h5: () => props => <h5 {...props} />,
  h6: () => props => <h6 {...props} />,
  a: () => props => <a {...props} />,
  img: () => props => <img {...props} />,
  table: () => props => <table {...props} />,
  tr: () => props => <tr {...props} />,
  td: () => props => <td {...props} />,
  th: () => props => <th {...props} />,
  thead: () => props => <thead {...props} />,
  tbody: () => props => <tbody {...props} />,
  tfoot: () => props => <tfoot {...props} />,
  label: () => props => <label {...props} />
};

// Add general support for any component
styled.div.withConfig = () => styled.div;
styled.div.attrs = () => styled.div;

// Add component factory support
styled.div.displayName = 'styled.div';
const styledFunction = component => component.displayName 
  ? React.forwardRef((props, ref) => React.createElement(component, { ...props, ref }))
  : styled.div;

Object.keys(styled).forEach(key => {
  styledFunction[key] = styled[key];
});

// Mock the ThemeProvider component
const ThemeProvider = ({ theme, children }) => (
  <div data-testid="styled-components-theme-provider">{children}</div>
);

// Mock other styled-components exports
const css = () => '';
const keyframes = () => '';
const createGlobalStyle = () => () => null;

module.exports = {
  __esModule: true,
  default: styledFunction,
  css,
  keyframes,
  ThemeProvider,
  createGlobalStyle,
  styled
}; 