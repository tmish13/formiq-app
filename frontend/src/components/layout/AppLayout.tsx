import React from 'react';
import { BottomNav } from '../organisms/BottomNav';
import { 
  Home, 
  Camera, 
  BarChart3, 
  Library, 
  User 
} from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
  showBottomNav?: boolean;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ 
  children, 
  showBottomNav = true 
}) => {
  const bottomNavItems = [
    {
      icon: <Home className="w-5 h-5" />,
      label: "Home",
      path: "/dashboard"
    },
    {
      icon: <Camera className="w-5 h-5" />,
      label: "Camera",
      path: "/record"
    },
    {
      icon: <BarChart3 className="w-5 h-5" />,
      label: "Progress",
      path: "/progress"
    },
    {
      icon: <Library className="w-5 h-5" />,
      label: "Library",
      path: "/analysis"
    },
    {
      icon: <User className="w-5 h-5" />,
      label: "Profile",
      path: "/profile"
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-blue-950/30 dark:to-purple-950/20">
      {children}
      
      {showBottomNav && (
        <BottomNav items={bottomNavItems} />
      )}
    </div>
  );
};

export default AppLayout;