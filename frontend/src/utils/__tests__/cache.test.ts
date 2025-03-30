import { apiCache } from '../cache';

describe('apiCache', () => {
  beforeEach(() => {
    apiCache.clear();
  });

  it('should set and get data', () => {
    const key = 'test:key';
    const data = { id: 1, name: 'Test' };

    apiCache.set(key, data);
    const result = apiCache.get(key);

    expect(result).toEqual(data);
  });

  it('should return null for non-existent key', () => {
    const result = apiCache.get('non:existent');
    expect(result).toBeNull();
  });

  it('should delete data', () => {
    const key = 'test:key';
    const data = { id: 1, name: 'Test' };

    apiCache.set(key, data);
    apiCache.delete(key);
    const result = apiCache.get(key);

    expect(result).toBeNull();
  });

  it('should clear all data', () => {
    const key1 = 'test:key1';
    const key2 = 'test:key2';
    const data1 = { id: 1, name: 'Test 1' };
    const data2 = { id: 2, name: 'Test 2' };

    apiCache.set(key1, data1);
    apiCache.set(key2, data2);
    apiCache.clear();

    expect(apiCache.get(key1)).toBeNull();
    expect(apiCache.get(key2)).toBeNull();
  });

  it('should handle different data types', () => {
    const key = 'test:key';
    const data = [1, 2, 3];

    apiCache.set(key, data);
    const result = apiCache.get(key);

    expect(result).toEqual(data);
  });

  it('should handle null values', () => {
    const key = 'test:key';
    const data = null;

    apiCache.set(key, data);
    const result = apiCache.get(key);

    expect(result).toBeNull();
  });
}); 