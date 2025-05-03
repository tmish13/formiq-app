import React from 'react';

// Create mock Material UI components
export const Container = ({ children, maxWidth, ...props }) => (
  <div data-testid="mui-container" {...props}>
    {children}
  </div>
);

export const Paper = ({ children, elevation, ...props }) => (
  <div data-testid="mui-paper" {...props}>
    {children}
  </div>
);

export const Typography = ({ children, variant, component, gutterBottom, align, ...props }) => {
  // Filter out MUI-specific props to avoid React DOM attribute warnings
  const filteredProps = { ...props };
  
  return (
    <div data-testid={`mui-typography-${variant || 'default'}`} {...filteredProps}>
      {children}
    </div>
  );
};

export const TextField = ({ label, type, value, onChange, margin, required, fullWidth, disabled, ...props }) => {
  // Filter out MUI-specific props to avoid React DOM attribute warnings
  const filteredProps = { ...props };
  delete filteredProps.variant;
  
  return (
    <div data-testid={`mui-textfield-${label ? label.toLowerCase() : 'default'}`}>
      <label htmlFor={`${label}-input`}>{label}</label>
      <input
        id={`${label}-input`}
        type={type || 'text'}
        value={value}
        onChange={onChange}
        required={required}
        disabled={disabled}
        aria-label={label}
        {...filteredProps}
      />
    </div>
  );
};

export const Button = ({ children, variant, color, type, disabled, fullWidth, size, ...props }) => {
  // Filter out MUI-specific props to avoid React DOM attribute warnings  
  const filteredProps = { ...props };
  delete filteredProps.sx; // Remove sx prop to avoid warnings
  
  return (
    <button 
      data-testid={`mui-button-${variant || 'default'}`}
      type={type || 'button'}
      disabled={disabled === true}
      {...filteredProps}
    >
      {children}
    </button>
  );
};

export const Link = ({ children, component, to, ...props }) => {
  // If component is specified, render that component
  if (component) {
    return React.createElement(component, { to, ...props }, children);
  }
  return <a href={to} {...props}>{children}</a>;
};

export const Box = ({ children, sx, display, justifyContent, alignItems, ...props }) => {
  // Filter out style props to avoid React DOM attribute warnings
  const filteredProps = { ...props };
  
  // Build a style object instead
  const style = {};
  if (display) style.display = display;
  if (justifyContent) style.justifyContent = justifyContent;
  if (alignItems) style.alignItems = alignItems;
  if (sx) {
    // In real app we'd process sx to CSS, here we just avoid the warning
  }
  
  return (
    <div data-testid="mui-box" style={style} {...filteredProps}>
      {children}
    </div>
  );
};

export const Alert = ({ children, severity, ...props }) => (
  <div data-testid={`mui-alert-${severity || 'default'}`} role="alert" {...props}>
    {children}
  </div>
);

// Mock material-ui components
export const CircularProgress = ({ size, color, 'aria-label': ariaLabel, ...props }) => (
  <span role="progressbar" data-testid="mui-circular-progress" aria-label={ariaLabel || "Loading"}>
    Loading...
  </span>
);
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