import { WebPlugin } from '@capacitor/core';

export enum CameraSource {
  Prompt = 'PROMPT',
  Camera = 'CAMERA',
  Photos = 'PHOTOS',
}

export enum CameraDirection {
  Rear = 'REAR',
  Front = 'FRONT',
}

export enum CameraResultType {
  Uri = 'uri',
  Base64 = 'base64',
  DataUrl = 'dataUrl',
}

export class Camera extends WebPlugin {
  constructor() {
    super();
  }

  async getPhoto() {
    return {
      path: 'mock/path/to/photo.jpg',
      webPath: 'mock/path/to/photo.jpg',
      format: 'jpeg',
      saved: true,
    };
  }

  async checkPermissions() {
    return { camera: 'granted' };
  }

  async requestPermissions() {
    return { camera: 'granted' };
  }
} 