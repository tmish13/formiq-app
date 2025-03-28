import { apiCache } from './cache';

describe('ApiCache', () => {
  beforeEach(() => {
    // Clear cache before each test
    apiCache.clear();
  });

  it('should store and retrieve data', () => {
    const testData = { id: 1, name: 'test' };
    apiCache.set('test-key', testData);
    
    const retrieved = apiCache.get('test-key');
    expect(retrieved).toEqual(testData);
  });

  it('should return null for non-existent keys', () => {
    const retrieved = apiCache.get('non-existent');
    expect(retrieved).toBeNull();
  });

  it('should clear all data', () => {
    apiCache.set('key1', 'value1');
    apiCache.set('key2', 'value2');
    
    apiCache.clear();
    
    expect(apiCache.get('key1')).toBeNull();
    expect(apiCache.get('key2')).toBeNull();
  });

  it('should handle different data types', () => {
    const stringData = 'test string';
    const numberData = 42;
    const objectData = { foo: 'bar' };
    const arrayData = [1, 2, 3];

    apiCache.set('string', stringData);
    apiCache.set('number', numberData);
    apiCache.set('object', objectData);
    apiCache.set('array', arrayData);

    expect(apiCache.get('string')).toBe(stringData);
    expect(apiCache.get('number')).toBe(numberData);
    expect(apiCache.get('object')).toEqual(objectData);
    expect(apiCache.get('array')).toEqual(arrayData);
  });

  it('should respect max size limit', () => {
    // Create a new cache instance with max size of 2
    const smallCache = new (apiCache.constructor as any)(5 * 60 * 1000, 2);

    smallCache.set('key1', 'value1');
    smallCache.set('key2', 'value2');
    smallCache.set('key3', 'value3');

    expect(smallCache.get('key1')).toBeNull(); // Oldest item should be removed
    expect(smallCache.get('key2')).toBe('value2');
    expect(smallCache.get('key3')).toBe('value3');
  });

  it('should handle cache expiration', () => {
    // Create a new cache instance with very short max age
    const shortCache = new (apiCache.constructor as any)(100, 100);

    shortCache.set('key', 'value');
    
    // Wait for cache to expire
    return new Promise(resolve => {
      setTimeout(() => {
        expect(shortCache.get('key')).toBeNull();
        resolve(undefined);
      }, 150);
    });
  });
}); 