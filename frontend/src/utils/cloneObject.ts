/**
 * Deep clones an object
 * @param obj The object to clone
 * @returns A deep clone of the input object
 */
export function cloneObject<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  // Handle Date
  if (obj instanceof Date) {
    return new Date(obj.getTime()) as unknown as T;
  }

  // Handle Array
  if (Array.isArray(obj)) {
    return obj.map(item => cloneObject(item)) as unknown as T;
  }

  // Handle Object
  if (obj instanceof Object) {
    try {
      const copy = {} as Record<string, unknown>;
      Object.entries(obj).forEach(([key, value]) => {
        copy[key] = cloneObject(value);
      });
      return copy as T;
    } catch (error) {
      // Fallback to JSON serialize/deserialize if regular cloning fails
      try {
        return JSON.parse(JSON.stringify(obj)) as T;
      } catch (jsonError) {
        console.warn('Failed to clone object using JSON.stringify/parse', jsonError);
        // Return a new empty object of the same constructor as a last resort
        return Object.create(Object.getPrototypeOf(obj)) as T;
      }
    }
  }

  // Fallback for other object types (Map, Set, FormData, etc.)
  try {
    return JSON.parse(JSON.stringify(obj)) as T;
  } catch (error) {
    console.warn(`Fallback: Unable to clone object using JSON methods: ${obj}`, error);
    return {} as T; // Return empty object as last resort instead of throwing
  }
}

export default cloneObject; 