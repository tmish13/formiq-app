import React from 'react';

// Mock material-ui components
export const Box = ({ children, ...rest }) => <div {...rest}>{children}</div>;
export const Button = ({ children, ...rest }) => <button {...rest}>{children}</button>;
export const Typography = ({ children, variant, ...rest }) => {
  const Tag = variant === 'h4' || variant === 'h6' ? variant : 'p';
  return <Tag {...rest}>{children}</Tag>;
};
export const CircularProgress = (props) => <div role="progressbar" aria-label={props['aria-label']}>Loading...</div>;
export const List = ({ children, ...rest }) => <ul {...rest}>{children}</ul>;
export const ListItem = ({ children, ...rest }) => <li {...rest}>{children}</li>;
export const ListItemText = ({ primary, secondary, ...rest }) => (
  <div {...rest}>
    <div>{primary}</div>
    {secondary && <div>{secondary}</div>}
  </div>
);

// Mock table components
export const Table = ({ children, ...rest }) => <table {...rest}>{children}</table>;
export const TableBody = ({ children, ...rest }) => <tbody {...rest}>{children}</tbody>;
export const TableCell = ({ children, ...rest }) => <td {...rest}>{children}</td>;
export const TableContainer = ({ children, ...rest }) => <div {...rest}>{children}</div>;
export const TableHead = ({ children, ...rest }) => <thead {...rest}>{children}</thead>;
export const TableRow = ({ children, ...rest }) => <tr {...rest}>{children}</tr>;
export const Paper = ({ children, ...rest }) => <div {...rest}>{children}</div>; 