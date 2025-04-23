# Theme Fixes Prioritization

This document categorizes the remaining theme issues that need manual fixes after running the automated theme audit tool.

## High Priority (Launch Blocking)

These issues affect the most frequently used components and could cause visual inconsistencies in the MVP.

### Common Components

1. **Button.tsx (15 issues)**
   - Direct color references without variants
   - References to fallbacks.typography

2. **Input.tsx (1 issue)**
   - Direct reference to colors.disabled

3. **ErrorMessage.tsx (9 issues)**
   - Direct error color references
   - Typography fallback references

4. **LoadingSpinner.tsx (8 issues)**
   - Direct color references
   - Typography fallback references

### Layout Components

1. **AppLayout.tsx (12 issues)**
   - Direct color references

2. **BottomTabNavigation.tsx & MobileNavigation.tsx (6 issues)**
   - Direct color references that affect cross-platform consistency

## Medium Priority (Fix if time permits before launch)

These affect important features but may not be as visually jarring.

1. **FormAnalysisResults.tsx (20 issues)**
   - Direct color references
   - Typography fallback references

2. **Progress.tsx & ProgressDashboard.tsx (19 issues)**
   - Direct color references in data visualization components

3. **PoseAnalysis.tsx (22 issues)**
   - Direct color references in visualization components

## Low Priority (Post-MVP)

These can be addressed in future sprints:

1. **SplashScreen.tsx (3 issues)**
2. **ErrorPage.tsx (4 issues)**
3. **SkeletonLoader.tsx (6 issues)**
4. **All page components (~70 issues)**
5. **utils/themeUtils.ts (7 issues)**

## Issue Types Breakdown

1. **Direct color references without variants (292 issues)**
   - Need to add appropriate variants (.main, .light, .dark, .primary, .secondary)

2. **References to fallbacks.typography (22 issues)**
   - Replace with direct fallbacks for specific properties

## Action Plan

1. Create JIRA tickets for each high-priority component
2. Schedule medium priority items for the week after MVP launch
3. Add low priority items to the backlog with "theme-fix" tag

## Estimate

- High priority: 3-4 developer hours
- Medium priority: 5-6 developer hours
- Low priority: 8-10 developer hours 