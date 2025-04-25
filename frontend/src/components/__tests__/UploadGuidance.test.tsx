import React from 'react';
import { testRender } from '../../test-utils';
import { UploadGuidance } from '../UploadGuidance';

describe('UploadGuidance', () => {
  const mockProps = {
    onChange: jest.fn()
  };

  it('renders without crashing', () => {
    const { getByTestId } = testRender(<UploadGuidance {...mockProps} />);
    expect(getByTestId('upload-guidance')).toBeInTheDocument();
  });

  it('matches snapshot', () => {
    const { asFragment } = testRender(<UploadGuidance {...mockProps} />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('displays upload guidance text', () => {
    const { getByText } = testRender(<UploadGuidance {...mockProps} />);
    expect(getByText(/Drag & drop your video here/i)).toBeInTheDocument();
  });

  it('displays supported file formats', () => {
    const { getByText } = testRender(<UploadGuidance {...mockProps} />);
    expect(getByText(/Supported formats: MP4, WebM, MOV/i)).toBeInTheDocument();
  });

  it('displays all guidance items', () => {
    const { getByText } = testRender(<UploadGuidance {...mockProps} />);
    expect(getByText(/Position your camera/i)).toBeInTheDocument();
    expect(getByText(/Ensure good lighting/i)).toBeInTheDocument();
    expect(getByText(/Record from the side angle/i)).toBeInTheDocument();
    expect(getByText(/Keep the camera stable/i)).toBeInTheDocument();
    expect(getByText(/Wear clothing/i)).toBeInTheDocument();
  });

  it('calls onChange when file is selected', () => {
    const { getByTestId } = testRender(<UploadGuidance {...mockProps} />);
    const fileInput = getByTestId('file-input');
    const file = new File(['test'], 'test.mp4', { type: 'video/mp4' });
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    
    Object.defineProperty(fileInput, 'files', {
      value: dataTransfer.files
    });
    
    const event = new Event('change', { bubbles: true });
    fileInput.dispatchEvent(event);
    
    expect(mockProps.onChange).toHaveBeenCalledWith(dataTransfer.files);
  });
}); 