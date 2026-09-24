# Frontend typecheck and test suite, recorded (plan item C7) — 2026-09-24

Nothing in `bench/results/`, the audits or the plans had ever recorded a frontend test run. This is the
first record; it is not green, and the new `frontend.yml` shows the same two facts as two jobs.

## Commands

```bash
cd frontend && npm run typecheck                      # tsc --noEmit
cd frontend && npm test -- --ci --watchAll=false      # jest --config jest.config.js
```

Environment: local, Node v22.22.3 / npm 10.9.8, `node_modules` as installed on this machine (the
lockfile requires `--legacy-peer-deps`: react-scripts 5.0.1 vs TypeScript 5). The working tree carried
the owner's uncommitted edits to `DashboardPage.tsx`, `RecordPage.tsx`, `TodayPlanCard.tsx` and
`InfoIcon.tsx`; none of the failing suites imports those files. CI runs the same two commands on a
clean install (`.github/workflows/frontend.yml`, jobs "Typecheck" and "Jest").

## Typecheck

```
error TS2688: Cannot find type definition file for '@testing-library/jest-dom'.
exit 2
```

One error, from `tsconfig.json:20` (`"types": ["jest", "node", "@testing-library/jest-dom"]`) against
`@testing-library/jest-dom@^6`, which no longer ships a type-reference package by that name. Whether it
reproduces on a clean install is what the CI job answers; the fix, if it does, is the `types` entry
(the matchers are already declared in `tests/jest-dom.d.ts`).

## Jest

```
Test Suites: 17 failed, 15 passed, 32 total
Tests:       94 failed, 493 passed, 587 total
Time:        23.153 s
```

Failing suites:

```
FAIL src/__tests__/nextSetRecommendation.test.ts
FAIL src/__tests__/workoutMode.test.tsx
FAIL src/features/training/__tests__/compatibility.test.ts
FAIL src/features/training/__tests__/EquipmentPickerDrawer.test.tsx
FAIL src/features/training/__tests__/ExercisePickerModal.test.tsx
FAIL tests/consolidated/ApiServices.consolidated.test.tsx
FAIL tests/consolidated/ErrorHandling.consolidated.test.tsx
FAIL tests/consolidated/SecurityAndPerformance.consolidated.test.tsx
FAIL tests/consolidated/UIComponents.consolidated.test.tsx
FAIL tests/consolidated/VideoPlayer.consolidated.test.tsx
FAIL tests/consolidated/VideoService.consolidated.test.tsx
FAIL tests/integration/api/basic-api-integration.test.tsx
FAIL tests/integration/mobile-native/camera-capture-upload.test.tsx
FAIL tests/integration/user-flows/authentication-flow.test.tsx
FAIL tests/integration/user-flows/offline-queue-functionality.test.tsx
FAIL tests/integration/user-flows/video-upload-analysis-flow.test.tsx
FAIL tests/unit/apiService.test.ts
```

Dominant error kinds (occurrences in the run):

| count | error |
|---|---|
| 80 | `TypeError: ... is not a function` (mocked services whose interface moved) |
| 8 | `Unable to find an element with the text: + Add custom` |
| 12 | `Unable to find an element by: [data-testid=...]` (`logged-in-view`, `form-check-list`, `exercise-list`, `user-profile`, `loading-indicator`) |
| 2 | `Cannot find module 'jsonwebtoken'` (a dev dependency the suite assumes) |
| 2 | `TypeError: Cannot read properties of undefined` |

`tests/broken-tests-backup/` (10 suites) is now ignored by `jest.config.js`; it was collected before
and is not counted above.

## What this is and is not

- The frontend suite has never been green in any record; it is red on a clean tree today. Filed as
  **G-56** (size M): the fix is a test-suite repair, not a five-minute closure, and is outside the
  approved scope. Until it is done, the "Jest" job is red on purpose.
- The typecheck is one config line away from green if CI confirms the error.
