declare module 'util' {
  export class TextEncoder {
    encode(input?: string): Uint8Array;
  }
  export class TextDecoder {
    decode(input?: Uint8Array | ArrayBuffer): string;
  }
} 