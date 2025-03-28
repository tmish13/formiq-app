export interface FormCheck {
  id: number;
  user_id: number;
  video_url: string;
  status: string;
  results?: Record<string, any>;
  created_at: string;
  updated_at?: string;
} 