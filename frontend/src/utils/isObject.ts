/**
 * Checks if a value is a plain object (not array, null, etc.)
 * @param value - The value to check
 * @returns True if the value is a plain object, false otherwise
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && 
         typeof value === 'object' && 
         !Array.isArray(value) && 
         Object.prototype.toString.call(value) === '[object Object]';
}

export default isObject; 