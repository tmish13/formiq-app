import { DefaultBodyType, MockedResponse, ResponseResolver, RestContext, RestRequest } from 'msw';

declare module 'msw' {
  interface ResponseComposition<T = any> {
    (body: T, init?: ResponseInit): MockedResponse<T>;
    json: (body: T, init?: ResponseInit) => MockedResponse<T>;
    status: (status: number) => ResponseComposition<T>;
  }

  interface RestContext {
    status: (status: number) => RestContext;
    json: <T = any>(body: T) => MockedResponse<T>;
  }

  type HandlerResponse<T = any> = ResponseResolver<RestRequest<T>, RestContext, DefaultBodyType>;

  interface MockedResponse<T = any> extends Response {
    once: () => MockedResponse<T>;
    passthrough: () => MockedResponse<T>;
  }

  interface ResponseTransformer<T = any> {
    (res: MockedResponse<T>): MockedResponse<T>;
  }
} 