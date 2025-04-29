// This file runs once before all tests
import { TextEncoder, TextDecoder } from 'util';

export default async () => {
  // Set up globals for all tests
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}; 