// Minimal styled-components mock to prevent test failures.
const React = require('react');

const tags = [
  'div', 'span', 'button', 'input', 'label', 'a', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'header', 'footer', 'nav', 'section', 'article', 'aside', 'main', 'form', 'ul', 'ol', 'li',
  'img', 'video', 'canvas', 'select', 'option', 'textarea', 'table', 'tr', 'th', 'td',
];

function createStyled(Tag) {
  const styledComponent = (...args) => {
    const Component = React.forwardRef((props, ref) => React.createElement(Tag, { ...props, ref }));
    Component.displayName = `styled(${typeof Tag === 'string' ? Tag : Tag.displayName || Tag.name})`;
    // Support chaining: styled.div`...`.attrs(...)
    Component.attrs = () => createStyled(Tag);
    Component.withConfig = () => createStyled(Tag);
    return Component;
  };
  styledComponent.attrs = () => createStyled(Tag);
  styledComponent.withConfig = () => createStyled(Tag);
  return styledComponent;
}

const styled = (Tag) => createStyled(Tag);

tags.forEach((tag) => {
  styled[tag] = createStyled(tag);
});

const css = (...args) => args;
const createGlobalStyle = () => () => null;
const keyframes = (...args) => 'animation';
const ThemeProvider = ({ children }) => children;
const ServerStyleSheet = class {
  collectStyles(children) { return children; }
  getStyleTags() { return ''; }
  getStyleElement() { return null; }
  seal() {}
};

module.exports = {
  default: styled,
  css,
  createGlobalStyle,
  keyframes,
  ThemeProvider,
  ServerStyleSheet,
  styled,
};
