# WebAssembly Pose Calculations

This directory contains the Rust code for our WebAssembly module that handles pose calculations for form analysis.

## Prerequisites

- Rust and Cargo (install via [rustup](https://rustup.rs/))
- wasm-pack (install via `cargo install wasm-pack`)

## Building

To build the WebAssembly module:

1. Make sure you have Rust and wasm-pack installed
2. Run the build script:
   ```bash
   ./scripts/build-wasm.sh
   ```

This will:
- Build the Rust code into WebAssembly
- Generate TypeScript type declarations
- Copy the built files to `src/wasm/`

## Usage

The WebAssembly module provides the following functions:

- `calculate_angle(p1: Point, p2: Point, p3: Point): number` - Calculates the angle between three points
- `calculate_distance(p1: Point, p2: Point): number` - Calculates the distance between two points
- `is_point_in_range(point: Point, center: Point, radius: number): boolean` - Checks if a point is within a given radius of a center point

Example usage:

```typescript
import { PoseCalculator } from '../wasm/pose_calculations';

// Calculate angle between three points
const angle = await PoseCalculator.calculateAngle(
  { x: 0, y: 0 },
  { x: 1, y: 1 },
  { x: 2, y: 0 }
);
```

## Development

When making changes to the Rust code:

1. Edit the Rust code in `src/lib.rs`
2. Run the build script to rebuild the WebAssembly module
3. The changes will be automatically picked up by the TypeScript code

## Testing

To test the WebAssembly module:

```bash
cargo test
```

This will run the Rust tests. For integration testing with TypeScript, see the test files in `src/__tests__/`. 