import React from 'react';

const createMockComponent = (name: string) => {
  return React.forwardRef((props: any, ref) => (
    <div data-testid={`mui-${name}`} ref={ref} {...props} />
  ));
};

export const Box = createMockComponent('box');
export const Typography = createMockComponent('typography');
export const Button = createMockComponent('button');
export const TextField = createMockComponent('textfield');
export const CircularProgress = createMockComponent('circular-progress');
export const Container = createMockComponent('container');
export const Paper = createMockComponent('paper');
export const Grid = createMockComponent('grid');
export const Card = createMockComponent('card');
export const CardContent = createMockComponent('card-content');
export const CardActions = createMockComponent('card-actions');
export const IconButton = createMockComponent('icon-button');
export const Dialog = createMockComponent('dialog');
export const DialogTitle = createMockComponent('dialog-title');
export const DialogContent = createMockComponent('dialog-content');
export const DialogActions = createMockComponent('dialog-actions'); 