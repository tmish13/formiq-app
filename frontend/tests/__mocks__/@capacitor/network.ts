import { WebPlugin } from '@capacitor/core';

export interface NetworkStatus {
  connected: boolean;
  connectionType: string;
}

export const Network = {
  getStatus: jest.fn().mockResolvedValue({
    connected: true,
    connectionType: 'wifi'
  }),
  
  addListener: jest.fn().mockReturnValue(Promise.resolve({
    remove: jest.fn().mockResolvedValue(undefined)
  }))
};

export default Network; 