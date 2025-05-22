import React from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions,
  Button
} from '@mui/material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../../store/rootReducer';
import { closeModal, ModalContent } from '../../store/slices/uiSlice';

export const ModalShell: React.FC = () => {
  const dispatch = useDispatch();
  const { isModalOpen, modalContent } = useSelector((state: RootState) => state.ui);

  const handleClose = () => {
    dispatch(closeModal());
  };

  if (!isModalOpen || !modalContent) {
    return null;
  }

  const { title, content, size = 'md' } = modalContent;

  return (
    <Dialog
      open={isModalOpen}
      onClose={handleClose}
      maxWidth={size as any}
      fullWidth
      aria-labelledby="modal-title"
      data-testid="modal-dialog"
    >
      {title && <DialogTitle id="modal-title" data-testid="modal-title">{title}</DialogTitle>}
      <DialogContent data-testid="modal-content">{content}</DialogContent>
      <DialogActions>
        <Button onClick={handleClose} data-testid="modal-close-button">Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModalShell; 