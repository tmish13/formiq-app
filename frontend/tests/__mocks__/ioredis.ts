// Mock implementation of Redis client
class Redis {
  private data: Map<string, string>;
  private eventHandlers: Map<string, Function[]>;

  constructor(config?: any) {
    this.data = new Map();
    this.eventHandlers = new Map();
  }

  async connect(): Promise<void> {
    return Promise.resolve();
  }

  async disconnect(): Promise<void> {
    return Promise.resolve();
  }

  async get(key: string): Promise<string | null> {
    return this.data.get(key) || null;
  }

  async set(key: string, value: string): Promise<'OK'> {
    this.data.set(key, value);
    return 'OK';
  }

  async setex(key: string, seconds: number, value: string): Promise<'OK'> {
    this.data.set(key, value);
    setTimeout(() => {
      this.data.delete(key);
    }, seconds * 1000);
    return 'OK';
  }

  async del(key: string): Promise<number> {
    return this.data.delete(key) ? 1 : 0;
  }

  async exists(key: string): Promise<number> {
    return this.data.has(key) ? 1 : 0;
  }

  async expire(key: string, seconds: number): Promise<number> {
    if (this.data.has(key)) {
      setTimeout(() => {
        this.data.delete(key);
      }, seconds * 1000);
      return 1;
    }
    return 0;
  }

  async flushall(): Promise<'OK'> {
    this.data.clear();
    return 'OK';
  }

  async quit(): Promise<'OK'> {
    return 'OK';
  }

  on(event: string, listener: Function): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)?.push(listener);
  }

  once(event: string, listener: Function): void {
    const onceListener = (...args: any[]) => {
      this.off(event, onceListener);
      listener(...args);
    };
    this.on(event, onceListener);
  }

  off(event: string, listener: Function): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      const index = handlers.indexOf(listener);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
    }
  }

  emit(event: string, ...args: any[]): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => handler(...args));
    }
  }

  removeListener(event: string, listener: Function): void {
    this.off(event, listener);
  }

  removeAllListeners(event?: string): void {
    if (event) {
      this.eventHandlers.delete(event);
    } else {
      this.eventHandlers.clear();
    }
  }
}

// Export Redis as both default and named export to support different import styles
export default Redis;
export { Redis }; 