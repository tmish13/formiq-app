// Enhanced design system with professional AI-focused color palette
export const designSystem = {
  typography: {
    // Enhanced typography scale with better hierarchy
    h1: "text-4xl font-bold leading-tight tracking-tight", // 36px
    h2: "text-2xl font-semibold leading-snug tracking-tight", // 24px
    h3: "text-xl font-medium leading-normal", // 20px
    body: "text-lg leading-relaxed", // 18px
    bodyMd: "text-base leading-normal", // 16px
    small: "text-sm leading-normal", // 14px
    xs: "text-xs leading-tight", // 12px
    // Enhanced stat numbers with tabular alignment
    statLarge: "text-4xl font-bold leading-none tabular-nums tracking-tight", // 36px, 700 weight
    statMedium: "text-3xl font-bold leading-none tabular-nums tracking-tight", // 30px, 700 weight
    statSmall: "text-2xl font-semibold leading-none tabular-nums", // 24px, 600 weight
    // Secondary data with lighter weights
    statSecondary: "text-sm font-normal leading-normal tabular-nums", // 14px, 400 weight
  },
  spacing: {
    // Increased vertical spacing for breathing room (+30px)
    cardGroup: "space-y-10", // 40px between card groups
    cardInternal: "p-8", // 32px internal padding (increased from 24px)
    sectionGap: "gap-10", // 40px gap between sections
    tagSpacing: "gap-4", // 16px between metric tags
    breathingRoom: "mb-12", // 48px bottom margin for sections
    heroSpacing: "mb-16", // 64px for hero sections
  },
  colors: {
    // Professional AI-focused color palette
    primary: {
      // Cool blues for tech/AI trust
      blue: "#0F172A", // Deep navy
      blueLight: "#1E293B", // Slate 800
      blueMedium: "#334155", // Slate 700
      blueAccent: "#3B82F6", // Blue 500
      blueGlow: "#60A5FA", // Blue 400
    },
    ai: {
      // Teal/neon green for AI feedback & success
      teal: "#0D9488", // Teal 600
      tealLight: "#14B8A6", // Teal 500
      tealGlow: "#5EEAD4", // Teal 300
      neonGreen: "#10B981", // Emerald 500
      neonGlow: "#6EE7B7", // Emerald 300
    },
    alert: {
      // Salmon/orange for warnings
      salmon: "#F97316", // Orange 500
      salmonLight: "#FB923C", // Orange 400
      warning: "#F59E0B", // Amber 500
      error: "#EF4444", // Red 500
    },
    neutral: {
      // Dark neutrals & off-whites
      50: "#FAFAFA", // Off-white instead of pure white
      100: "#F5F5F5", // Light gray
      200: "#E5E5E5", // Gray 200
      300: "#D4D4D4", // Gray 300
      400: "#A3A3A3", // Gray 400
      500: "#737373", // Gray 500
      600: "#525252", // Gray 600
      700: "#404040", // Gray 700
      800: "#262626", // Gray 800
      900: "#171717", // Almost black
    },
  },
  gradients: {
    // Subtle gradients with transparency
    aiPrimary: "bg-gradient-to-r from-slate-900 via-slate-800 to-transparent",
    aiSecondary: "bg-gradient-to-br from-teal-600/20 via-blue-600/10 to-transparent",
    success: "bg-gradient-to-r from-emerald-500/20 to-teal-500/10",
    warning: "bg-gradient-to-r from-orange-500/20 to-amber-500/10",
    hero: "bg-gradient-to-br from-slate-50 via-blue-50/50 to-teal-50/30",
    heroDark: "bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900",
    card: "bg-gradient-to-br from-white to-slate-50/50",
    cardDark: "bg-gradient-to-br from-slate-800 to-slate-900/50",
    aiGlow: "bg-gradient-to-r from-teal-500/30 via-blue-500/20 to-purple-500/30",
  },
  shadows: {
    // More subtle shadows and borders
    card: "shadow-sm border border-slate-200/50 dark:border-slate-700/50",
    cardHover: "shadow-lg border border-slate-300/50 dark:border-slate-600/50",
    cardElevated: "shadow-xl border border-slate-200/50 dark:border-slate-700/50",
    glow: "shadow-lg shadow-teal-500/20",
    aiGlow: "shadow-2xl shadow-teal-500/30",
  },
  animations: {
    cardHover: "hover:scale-[1.02] hover:-translate-y-2 transition-all duration-300 ease-out",
    cardTilt: "hover:rotate-1 transition-transform duration-300 ease-out",
    iconTilt: "hover:rotate-12 transition-transform duration-200 ease-out",
    buttonTap: "active:scale-95 transition-transform duration-100",
    fadeIn: "animate-in fade-in duration-500",
    slideUp: "animate-in slide-in-from-bottom-6 duration-500",
    bounce: "animate-bounce",
    pulse: "animate-pulse",
    spin: "animate-spin",
  },
}

// AI-themed visual elements
export const aiVisuals = {
  neuronPattern: `
    <svg className="absolute inset-0 w-full h-full opacity-5" viewBox="0 0 100 100">
      <defs>
        <pattern id="neuron" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
          <circle cx="10" cy="10" r="1" fill="currentColor"/>
          <line x1="10" y1="10" x2="15" y2="5" stroke="currentColor" strokeWidth="0.5"/>
          <line x1="10" y1="10" x2="5" y2="15" stroke="currentColor" strokeWidth="0.5"/>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#neuron)"/>
    </svg>
  `,
  brainGlow:
    "before:absolute before:inset-0 before:bg-gradient-to-r before:from-teal-500/20 before:to-blue-500/20 before:blur-xl before:rounded-full",
}

// WCAG AA compliant color combinations with new palette
export const accessibleColors = {
  text: {
    primary: "text-slate-900 dark:text-slate-50", // 15:1 contrast
    secondary: "text-slate-700 dark:text-slate-200", // 7:1 contrast
    muted: "text-slate-600 dark:text-slate-300", // 4.5:1 contrast
    inverse: "text-white dark:text-slate-900",
    accent: "text-teal-600 dark:text-teal-400",
  },
  backgrounds: {
    primary: "bg-slate-50 dark:bg-slate-900",
    secondary: "bg-white dark:bg-slate-800",
    card: "bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm",
    overlay: "bg-slate-900/50 dark:bg-slate-900/70",
    ai: "bg-gradient-to-br from-teal-50 to-blue-50 dark:from-slate-800 dark:to-slate-900",
  },
}
