// Temporary type fixes to help with TypeScript compilation

declare module '*.css' {
  const content: { [className: string]: string };
  export default content;
}

declare module '*.module.css' {
  const classes: { [key: string]: string };
  export default classes;
}

// Extend the User type temporarily to include missing properties
declare module './user' {
  interface User {
    firstName?: string;
    lastName?: string;
  }
}