export interface AppSettings {
  theme?: 'light' | 'dark' | 'system';
  notifications?: {
    email_updates?: boolean;
    exercise_reminders?: boolean;
    form_check_results?: boolean;
    achievement_alerts?: boolean;
  };
  privacy?: {
    profile_public?: boolean;
    show_progress?: boolean;
    share_achievements?: boolean;
  };
  language?: 'en' | 'es' | 'fr' | 'de' | 'it' | 'pt' | 'ru' | 'zh';
  exercise_preferences?: {
    preferred_exercises?: string[];
    difficulty_level?: 'beginner' | 'intermediate' | 'advanced';
    workout_duration?: number;
    equipment_available?: string[];
  };
} 