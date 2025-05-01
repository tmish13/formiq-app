// Mock for miscUtil
export function getValue<T>(value: T) {
  return value;
}

export function scrollTo(element: HTMLElement, to: number, duration: number) {
  // Mock implementation
}

export function waitElementReady(element: HTMLElement) {
  return Promise.resolve(element);
}

export default {
  getValue,
  scrollTo,
  waitElementReady,
}; 