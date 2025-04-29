// Mock implementation of @capacitor/network
class MockNetwork {
  async getStatus() {
    return {
      connected: true,
      connectionType: 'wifi'
    };
  }

  async addListener(_eventName: string, _listenerFunc: Function) {
    return {
      remove: () => {}
    };
  }

  async removeAllListeners() {
    return;
  }
}

const Network = new MockNetwork();
export { Network }; 