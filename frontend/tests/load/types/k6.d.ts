declare module 'k6' {
  export function check(val: any, sets: { [key: string]: (val: any) => boolean }): void;
  export function group(name: string, fn: () => void): void;
  export function sleep(seconds: number): void;
  export const __ENV: { [key: string]: string };
  export const __VU: number;
}

declare module 'k6/http' {
  interface Response {
    status: number;
    body: string;
    json(selector?: string): any;
  }

  interface RequestParams {
    headers?: { [key: string]: string };
    tags?: { [key: string]: string };
    timeout?: number;
  }

  export function post(url: string, payload?: any, params?: RequestParams): Response;
  export function get(url: string, params?: RequestParams): Response;
}

declare module 'k6/metrics' {
  export class Trend {
    constructor(name: string);
    add(value: number): void;
  }

  export class Rate {
    constructor(name: string);
    add(value: number): void;
  }

  export class Counter {
    constructor(name: string);
    add(value: number): void;
  }

  export class Gauge {
    constructor(name: string);
    add(value: number): void;
  }
}

declare module 'k6/options' {
  interface Stage {
    duration: string;
    target: number;
  }

  interface Scenario {
    executor: string;
    startVUs?: number;
    stages?: Stage[];
    gracefulRampDown?: string;
    rate?: number;
    timeUnit?: string;
    duration?: string;
    preAllocatedVUs?: number;
    maxVUs?: number;
    vus?: number;
    iterations?: number;
    startTime?: string;
  }

  export interface Options {
    scenarios: {
      [key: string]: Scenario;
    };
    thresholds?: {
      [key: string]: string[];
    };
  }
} 