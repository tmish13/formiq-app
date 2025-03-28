import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

declare class ErrorBoundary extends Component<Props> {}

export default ErrorBoundary; 