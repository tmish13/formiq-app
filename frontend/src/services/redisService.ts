import Redis from 'ioredis';

interface RedisError extends Error {
  code?: string;
  errno?: number;
  syscall?: string;
}

class RedisService {
  private client: Redis;
  private readonly DEFAULT_TTL = 3600; // 1 hour in seconds

  constructor() {
    this.client = new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD,
    });

    this.client.on('error', (err: RedisError) => {
      console.error('Redis Client Error:', err);
    });
  }

  async get<T>(key: string): Promise<T | null> {
    try {
      const value = await this.client.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error('Redis Get Error:', error);
      return null;
    }
  }

  async set(key: string, value: any, ttl: number = this.DEFAULT_TTL): Promise<void> {
    try {
      await this.client.setex(key, ttl, JSON.stringify(value));
    } catch (error) {
      console.error('Redis Set Error:', error);
    }
  }

  async delete(key: string): Promise<void> {
    try {
      await this.client.del(key);
    } catch (error) {
      console.error('Redis Delete Error:', error);
    }
  }

  async clear(): Promise<void> {
    try {
      await this.client.flushall();
    } catch (error) {
      console.error('Redis Clear Error:', error);
    }
  }

  generateKey(url: string, params?: any): string {
    const baseKey = `api:${url}`;
    return params ? `${baseKey}:${JSON.stringify(params)}` : baseKey;
  }
}

export const redisService = new RedisService(); 