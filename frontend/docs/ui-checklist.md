# FormIQ UI Consistency Checklist

This document serves as a guide for checking visual consistency across the FormIQ frontend before MVP launch.

## Typography Consistency

### Font Families
- [ ] Primary font (`font-family: ${({ theme }) => theme.typography.fontFamily.primary}`) used for all body text
- [ ] Secondary font (`font-family: ${({ theme }) => theme.typography.fontFamily.secondary}`) used for headings only
- [ ] Mono font (`font-family: ${({ theme }) => theme.typography.fontFamily.mono}`) used for code blocks or technical data only

### Font Sizes
- [ ] Consistent use of theme.typography.fontSize tokens (xs, sm, md, lg, xl, xxl)
- [ ] Headings follow consistent hierarchy:
  - h1: xl or xxl
  - h2: lg
  - h3: md
  - h4: sm
- [ ] Body text consistently uses md (or sm for secondary text)

### Font Weights
- [ ] Consistent application of font weights:
  - Regular (400) for most text
  - Medium (500) for emphasis
  - Bold (700) for headings and important UI elements

## Component Styling

### Buttons
- [ ] Primary buttons use theme.colors.primary.main
- [ ] Secondary buttons use theme.colors.secondary.main or transparent background
- [ ] Disabled state has consistent styling
- [ ] Hover/active states follow the same pattern
- [ ] Button heights consistent within same context:
  - Primary actions: 44px (mobile), 48px (desktop)
  - Secondary actions: 36px
  - Tertiary/icon actions: 32px
- [ ] Button text is properly cased (Title Case or Sentence case, but consistent)

### Inputs & Forms
- [ ] Input heights are consistent (44px)
- [ ] Form field spacing is consistent (16px or 24px between fields)
- [ ] Labels are consistently positioned and styled
- [ ] Error states have consistent styling
- [ ] Input borders use consistent color (theme.colors.border.main or related variant)
- [ ] Focus states have consistent styling
- [ ] Helper text and error messages use consistent styling

### Cards & Containers
- [ ] Card padding is consistent (usually theme.spacing.lg)
- [ ] Card borders and shadows follow a consistent pattern
- [ ] Background colors adhere to theme
- [ ] Margins between cards are consistent

### Navigation
- [ ] Tab/navigation item spacing is consistent
- [ ] Active/selected states are visually consistent
- [ ] Navigation bars use consistent elevation (shadows) 
- [ ] Navigation typography (size, weight) is consistent

## Layout & Spacing

### Grid System
- [ ] Components align to a consistent grid
- [ ] Section spacing is consistent throughout the app
- [ ] Margins and paddings use theme spacing tokens exclusively

### Responsive Behavior
- [ ] Components adjust appropriately across breakpoints
- [ ] Spacing scales appropriately on different devices
- [ ] Touch targets are appropriately sized on mobile (minimum 44px)

### Alignment
- [ ] Text alignment is consistent (left-aligned for LTR languages)
- [ ] Form elements have consistent alignment
- [ ] Headers and footers maintain consistent alignment

## Color Usage

### Primary Colors
- [ ] Primary brand color used only for important actions and key UI elements
- [ ] Secondary color used consistently for complementary elements
- [ ] Color usage aligns with their semantic meanings

### Feedback Colors
- [ ] Success states consistently use theme.colors.success.main
- [ ] Error states consistently use theme.colors.error.main
- [ ] Warning states consistently use theme.colors.warning.main
- [ ] Info states consistently use theme.colors.info.main

### Background & Text
- [ ] Background colors are from the theme palette
- [ ] Text colors provide sufficient contrast (WCAG AA compliant)
- [ ] Text on colored backgrounds uses appropriate contrasting colors

## Cross-Platform Consistency

### Device-Specific Checks
- [ ] iPhone 13 Pro
  - [ ] Elements properly sized for touch
  - [ ] Text readable without zooming
  - [ ] UI elements don't overflow or get cut off

- [ ] Pixel 6
  - [ ] Elements properly sized for touch
  - [ ] Text readable without zooming
  - [ ] UI elements don't overflow or get cut off

- [ ] iPad Pro
  - [ ] Layout takes advantage of larger screen space
  - [ ] Text and UI elements properly scaled
  - [ ] Touch targets appropriately sized

- [ ] Desktop (1280x800)
  - [ ] UI takes advantage of available space
  - [ ] Hover states properly implemented
  - [ ] Keyboard navigation works as expected

## Accessibility

- [ ] Color contrast meets WCAG AA standards
- [ ] Touch targets are at least 44x44px on mobile
- [ ] Focus states are visible for keyboard navigation
- [ ] Text is readable at the set font size
- [ ] Interactive elements are identifiable

## Flow-Specific Consistency

### Login Flow
- [ ] Input fields match the design system
- [ ] Error messages are consistently displayed
- [ ] Buttons follow the primary action styling

### Workout Tracking Flow
- [ ] Exercise cards have consistent styling
- [ ] Progress indicators follow the same visual language
- [ ] Add/remove actions use consistent iconography and styling

### Form Analysis Flow
- [ ] Analysis results presented with consistent visual hierarchy
- [ ] Feedback messages styled consistently
- [ ] Video/image capture UI consistently styled

## Next Steps

After completing this checklist:
1. Document any inconsistencies found
2. Create tickets for issues that need to be fixed before launch
3. Tag lower-priority visual issues for post-launch improvements
4. Update BackstopJS tests to verify visual consistency 

## Cross-Device and Real-World Mobile Testing

- [ ] iPhone 13/14
  - [ ] Test portrait orientation
  - [ ] Test landscape orientation
  - [ ] Camera access functions properly
  - [ ] Navigation gestures work as expected
  - [ ] Form upload experience is smooth
  - [ ] Feedback experience is consistent

- [ ] iPad
  - [ ] Test portrait orientation
  - [ ] Test landscape orientation
  - [ ] Camera access functions properly
  - [ ] Navigation gestures work as expected
  - [ ] Form upload experience is smooth
  - [ ] Feedback experience is consistent

- [ ] Pixel 6+
  - [ ] Test portrait orientation
  - [ ] Test landscape orientation
  - [ ] Camera access functions properly
  - [ ] Navigation gestures work as expected
  - [ ] Form upload experience is smooth
  - [ ] Feedback experience is consistent

## Security and Privacy Checks

- [ ] Remove all console.log statements
- [ ] Remove any hardcoded tokens
- [ ] Remove development endpoints
- [ ] Implement Content Security Policy (CSP) headers if using NGINX
- [ ] Obfuscate sensitive logic (e.g., session handling)

## Performance Optimization

- [ ] Utilize source-map-explorer or webpack-bundle-analyzer to identify:
  - [ ] Bloated dependencies
  - [ ] Duplicated modules
- [ ] Enable lazy loading for large routes and assets
- [ ] Optimize image assets (convert to WebP where possible)

## Static Build Audit

- [ ] Verify production build (yarn build) meets requirements:
  - [ ] Main bundle size less than 1.5MB gzipped
  - [ ] Proper file naming conventions with hashing for cache busting
  - [ ] No uncompressed assets in public directory

## User Experience (UX) and Accessibility Enhancements

- [ ] Improve form input accessibility and validation:
  - [ ] Ensure intuitive keyboard navigation
  - [ ] Provide clear error states
  - [ ] Manage focus handling and auto-scrolling to errors

## User Onboarding and Feedback Mechanisms

- [ ] Introduce tooltips or short onboarding hints for new users:
  - [ ] Upload guidance
  - [ ] Expectations after feedback is generated
- [ ] Consider adding a "Help" or "FAQ" section (UI or modal) 