# Frontend UI Coexistence Strategy

## Overview
This document outlines how Material-UI and shadcn/ui components will coexist during the migration period.

## Systems in Use

### Current: Material-UI + Styled Components
- **Location**: `src/components/` (various subdirectories)
- **Styling**: Styled Components with theme system
- **Examples**: `src/components/common/Button.tsx`, Material-UI components

### New: shadcn/ui + Tailwind CSS
- **Location**: `src/components/ui/`
- **Styling**: Tailwind CSS with CSS variables
- **Examples**: `src/components/ui/button.tsx`, Radix UI components

## Migration Strategy

### Phase 1: Infrastructure ✅
- [x] Install shadcn/ui dependencies
- [x] Configure Tailwind CSS
- [x] Set up component structure
- [x] Import all shadcn/ui components

### Phase 2: Core Component Migration
1. **Button** → Replace `common/Button.tsx` with `ui/button.tsx`
2. **Input** → Replace `common/Input.tsx` with `ui/input.tsx`
3. **Card** → Replace custom cards with `ui/card.tsx`
4. **Badge** → Replace custom badges with `ui/badge.tsx`

### Phase 3: Page Migration
- Gradually replace Material-UI components with shadcn/ui
- Preserve all business logic and API integrations
- Maintain mobile compatibility (Capacitor)

## Component Mapping

| Current Component | New Component | Status |
|------------------|---------------|---------|
| `common/Button.tsx` | `ui/button.tsx` | Pending |
| `common/Input.tsx` | `ui/input.tsx` | Pending |
| Material-UI Cards | `ui/card.tsx` | Pending |
| Custom Progress | `ui/progress.tsx` | Pending |
| Material-UI Dialog | `ui/dialog.tsx` | Pending |

## Import Strategy

### Gradual Replacement
```typescript
// Old (being phased out)
import { Button } from '../components/common/Button';

// New (preferred for new features)
import { Button } from '../components/ui/button';
```

### Feature Preservation
- All existing props and functionality maintained
- API integrations preserved
- Mobile gestures and Capacitor compatibility maintained
- Theme system gradually migrated to CSS variables

## Testing Strategy
- Both UI systems tested during migration
- Existing test suite maintained
- New components tested with same standards
- Mobile builds verified continuously

## Timeline
- **Week 1**: Core components (Button, Input, Card)
- **Week 2**: Form components and validation
- **Week 3**: Page-level migrations
- **Week 4**: Mobile testing and cleanup

## Benefits
- Modern, accessible UI components (Radix UI)
- Better developer experience (Tailwind CSS)
- Improved performance (tree-shaking)
- Future-proof architecture
- Maintained functionality and compatibility