import React from 'react';
import { testRender, act } from '../../test-utils';
import VideoPlayer from '../VideoPlayer';

describe('VideoPlayer', () => {
  const mockVideoUrl = 'https://example.com/video.mp4';

  it('renders without crashing', () => {
    const { getByTestId } = testRender(<VideoPlayer src={mockVideoUrl} />);
    expect(getByTestId('video-player')).toBeInTheDocument();
  });

  it('matches snapshot', () => {
    const { asFragment } = testRender(<VideoPlayer src={mockVideoUrl} />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('displays loading state when video is not ready', () => {
    const { getByTestId } = testRender(<VideoPlayer src={mockVideoUrl} />);
    expect(getByTestId('video-loading')).toBeInTheDocument();
  });

  it('handles video error state', async () => {
    const { getByTestId } = testRender(<VideoPlayer src="invalid-url" />);
    const video = getByTestId('video-player').querySelector('video');
    
    await act(async () => {
      if (video) {
        video.dispatchEvent(new Event('error'));
      }
    });

    expect(getByTestId('video-error')).toBeInTheDocument();
  });
}); 