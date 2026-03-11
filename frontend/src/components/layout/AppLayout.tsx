import React from 'react';
import { useNavigate } from 'react-router-dom';
import { BottomNav } from '../organisms/BottomNav';
import {
  Home,
  Camera,
  BarChart3,
  Dumbbell,
  User,
  Settings,
  Brain,
} from 'lucide-react';
import { Button } from '../ui/button';
import UnverifiedBanner from '../auth/UnverifiedBanner';

interface AppLayoutProps {
  children: React.ReactNode;
  showBottomNav?: boolean;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  showBottomNav = true
}) => {
  const navigate = useNavigate();
  const bottomNavItems = [
    { icon: Home,     label: "Home",     path: "/dashboard" },
    { icon: Camera,   label: "Record",   path: "/record"    },
    { icon: BarChart3, label: "Progress", path: "/progress"  },
    { icon: Dumbbell, label: "Train",    path: "/workouts"  },
    { icon: User,     label: "Profile",  path: "/profile"   },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Fixed header — paddingTop absorbs iOS status-bar / Dynamic Island safe area */}
      <header
        className="fixed top-0 left-0 right-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 backdrop-blur-md"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        <div className="mx-auto max-w-[430px] h-16 flex items-center justify-between px-4">
          {/* Left — FormIQ branding */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 flex items-center justify-center flex-shrink-0">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-gray-900 dark:text-white leading-tight">FormIQ</h1>
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-violet-100 text-violet-600 dark:bg-violet-900/40 dark:text-violet-300 leading-none">
                Beta
              </span>
            </div>
          </div>

          {/* Right — Settings */}
          <div className="flex items-center">
            <Button
              variant="ghost"
              size="sm"
              className="text-gray-600 dark:text-gray-400"
              onClick={() => navigate('/profile')}
              aria-label="Profile settings"
            >
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Spacer matching full header height (status bar + 64px content) */}
      <div style={{ height: 'calc(64px + env(safe-area-inset-top))' }} aria-hidden="true" />

      {/* Beta: shown when user is logged in but email not yet verified */}
      <UnverifiedBanner />

      {/* Page content constrained to 430px */}
      <div className="mx-auto max-w-[430px] relative">
        {children}
      </div>

      {showBottomNav && (
        <BottomNav items={bottomNavItems} />
      )}
    </div>
  );
};

export default AppLayout;
