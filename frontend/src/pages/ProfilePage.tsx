import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Bell,
  Shield,
  HelpCircle,
  LogOut,
  Edit3,
  Camera,
  Moon,
  Smartphone,
  RotateCcw,
  ChevronRight,
  AlertTriangle,
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Badge } from '../components/ui/badge';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../hooks/use-toast';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import { logout } from '../store/slices/authSlice';
import { progressService } from '../services/progressService';
import AppLayout from '../components/layout/AppLayout';

interface UserStats {
  totalAnalyses: number;
  avgFormScore: number;
  currentStreak: number;
  joinDate: string;
}

export default function ProfilePage() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { toast } = useToast();
  const user = useSelector((state: RootState) => state.auth.user);
  
  const [darkMode, setDarkMode] = useState(false);
  const [notifications, setNotifications] = useState(true);
  const [autoRecord, setAutoRecord] = useState(false);
  const [userStats, setUserStats] = useState<UserStats>({
    totalAnalyses: 0,
    avgFormScore: 0,
    currentStreak: 0,
    joinDate: 'January 2024',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUserData();
    loadPreferences();
  }, []);

  const loadUserData = async () => {
    try {
      // Load progress overview from backend
      const progressOverview = await progressService.getProgressOverview();
      setUserStats({
        totalAnalyses: progressOverview.totalSessions,
        avgFormScore: Math.round(progressOverview.averageScore),
        currentStreak: progressOverview.currentStreak,
        joinDate: 'January 2024', // This would come from user registration date
      });
    } catch (error) {
      console.error('Failed to load user stats:', error);
      // Use fallback data
      setUserStats({
        totalAnalyses: 0,
        avgFormScore: 0,
        currentStreak: 0,
        joinDate: 'January 2024',
      });
    } finally {
      setLoading(false);
    }
  };

  const loadPreferences = () => {
    // Load theme preference
    const savedTheme = localStorage.getItem('formiq-theme');
    if (savedTheme === 'dark') {
      setDarkMode(true);
      document.documentElement.classList.add('dark');
    }

    // Load notification preference
    const savedNotifications = localStorage.getItem('formiq-notifications');
    if (savedNotifications !== null) {
      setNotifications(JSON.parse(savedNotifications));
    }

    // Load auto-record preference
    const savedAutoRecord = localStorage.getItem('formiq-auto-record');
    if (savedAutoRecord !== null) {
      setAutoRecord(JSON.parse(savedAutoRecord));
    }
  };

  const handleThemeToggle = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('formiq-theme', 'dark');
      toast({
        title: '✅ Dark Mode Enabled',
        description: 'Interface switched to dark theme',
        duration: 2000,
      });
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('formiq-theme', 'light');
      toast({
        title: '☀️ Light Mode Enabled',
        description: 'Interface switched to light theme',
        duration: 2000,
      });
    }
  };

  const handleNotificationsToggle = () => {
    const newNotifications = !notifications;
    setNotifications(newNotifications);
    localStorage.setItem('formiq-notifications', JSON.stringify(newNotifications));
    
    toast({
      title: newNotifications ? '✅ Notifications Enabled' : '⚠️ Notifications Disabled',
      description: newNotifications ? "You'll receive workout reminders" : 'Workout reminders turned off',
      duration: 2000,
    });
  };

  const handleAutoRecordToggle = () => {
    const newAutoRecord = !autoRecord;
    setAutoRecord(newAutoRecord);
    localStorage.setItem('formiq-auto-record', JSON.stringify(newAutoRecord));
    
    toast({
      title: newAutoRecord ? '✅ Auto-Record Enabled' : '⚠️ Auto-Record Disabled',
      description: newAutoRecord ? 'Recording will start automatically' : 'Manual recording required',
      duration: 2000,
    });
  };

  const resetApp = () => {
    localStorage.removeItem('formiq-auth-token');
    localStorage.removeItem('formiq-onboarding-complete');
    localStorage.removeItem('formiq-user-progress');
    localStorage.removeItem('formiq-theme');
    localStorage.removeItem('formiq-notifications');
    localStorage.removeItem('formiq-auto-record');
    
    toast({
      title: '🔄 Demo Reset Complete',
      description: 'All demo data has been cleared',
      duration: 3000,
    });
    
    // Clear Redux state and navigate
    dispatch(logout());
    navigate('/auth');
  };

  const handleLogout = () => {
    toast({
      title: '👋 Signed Out',
      description: "You've been successfully signed out",
      duration: 2000,
    });
    
    // Clear Redux state and navigate
    dispatch(logout());
    navigate('/auth');
  };

  const settingsGroups = [
    {
      title: 'Preferences',
      items: [
        {
          icon: <Moon className="w-5 h-5" />,
          label: 'Dark Mode',
          description: 'Switch between light and dark themes',
          action: <Switch checked={darkMode} onCheckedChange={handleThemeToggle} className="ml-auto" />,
          clickable: true,
          onClick: handleThemeToggle,
        },
        {
          icon: <Bell className="w-5 h-5" />,
          label: 'Notifications',
          description: 'Receive workout reminders and tips',
          action: <Switch checked={notifications} onCheckedChange={handleNotificationsToggle} className="ml-auto" />,
          clickable: true,
          onClick: handleNotificationsToggle,
        },
        {
          icon: <Smartphone className="w-5 h-5" />,
          label: 'Auto-Record',
          description: "Start recording automatically when you're in position",
          action: <Switch checked={autoRecord} onCheckedChange={handleAutoRecordToggle} className="ml-auto" />,
          clickable: true,
          onClick: handleAutoRecordToggle,
        },
      ],
    },
    {
      title: 'Account',
      items: [
        {
          icon: <Edit3 className="w-5 h-5" />,
          label: 'Edit Profile',
          description: 'Update your personal information',
          action: <ChevronRight className="w-5 h-5 text-gray-400" />,
          clickable: true,
          onClick: () => {
            toast({
              title: 'Coming Soon',
              description: 'Profile editing will be available in a future update',
              duration: 2000,
            });
          },
        },
        {
          icon: <Shield className="w-5 h-5" />,
          label: 'Privacy & Security',
          description: 'Manage your privacy settings',
          action: <ChevronRight className="w-5 h-5 text-gray-400" />,
          clickable: true,
          onClick: () => {
            toast({
              title: 'Coming Soon',
              description: 'Privacy settings will be available in a future update',
              duration: 2000,
            });
          },
        },
      ],
    },
    {
      title: 'Support',
      items: [
        {
          icon: <HelpCircle className="w-5 h-5" />,
          label: 'Help & Support',
          description: 'Get help and contact support',
          action: <ChevronRight className="w-5 h-5 text-gray-400" />,
          clickable: true,
          onClick: () => {
            toast({
              title: 'Contact Support',
              description: 'Email us at support@formiq.ai for assistance',
              duration: 3000,
            });
          },
        },
        {
          icon: <RotateCcw className="w-5 h-5" />,
          label: 'Reset Demo',
          description: 'Reset all demo data and start fresh',
          subDescription: 'This will erase all your demo data',
          action: (
            <Button
              variant="ghost"
              size="sm"
              onClick={resetApp}
              className="text-orange-600 hover:text-orange-700 hover:bg-orange-50 dark:hover:bg-orange-900/20"
            >
              Reset
            </Button>
          ),
          clickable: false,
        },
      ],
    },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <AppLayout>
      <div className="px-4 py-6 space-y-8 max-w-4xl mx-auto pb-24" style={{ paddingBottom: "max(env(safe-area-inset-bottom), 24px)" }}>
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">Profile</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage your account and preferences</p>
        </motion.div>

        {/* Enhanced Profile Card */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="bg-gradient-to-br from-white via-blue-50/30 to-purple-50/30 dark:from-gray-800 dark:via-blue-950/20 dark:to-purple-950/20 backdrop-blur-sm shadow-xl border-0">
            <CardContent className="p-8">
              <div className="flex items-center space-x-6 mb-8">
                <div className="relative">
                  <Avatar className="w-24 h-24 ring-4 ring-white/50 dark:ring-gray-700/50">
                    <AvatarImage src="/placeholder.svg?height=96&width=96&text=User" />
                    <AvatarFallback className="bg-gradient-to-br from-purple-500 to-indigo-600 text-white text-2xl font-bold">
                      {user?.firstName?.[0] || user?.email?.[0]?.toUpperCase() || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    className="absolute -bottom-1 -right-1 w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center text-white hover:bg-purple-700 transition-colors shadow-lg"
                    onClick={() => {
                      toast({
                        title: 'Coming Soon',
                        description: 'Profile photo upload will be available soon',
                        duration: 2000,
                      });
                    }}
                  >
                    <Camera className="w-5 h-5" />
                  </motion.button>
                </div>
                <div className="flex-1">
                  <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
                    {user?.firstName && user?.lastName 
                      ? `${user.firstName} ${user.lastName}`
                      : user?.email?.split('@')[0] || 'Demo User'
                    }
                  </h2>
                  <p className="text-gray-600 dark:text-gray-400 mb-3">
                    {user?.email || 'demo@formiq.ai'}
                  </p>
                  <div className="flex items-center space-x-3">
                    <Badge
                      variant="secondary"
                      className="bg-gradient-to-r from-purple-100 to-indigo-100 dark:from-purple-900/30 dark:to-indigo-900/30 text-purple-700 dark:text-purple-300 font-semibold px-3 py-1"
                    >
                      Free Plan
                    </Badge>
                    <Badge variant="outline" className="text-xs border-gray-300 dark:border-gray-600">
                      Member since {userStats.joinDate}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Enhanced Stats */}
              <div className="grid grid-cols-3 gap-6 pt-6 border-t border-gray-200/60 dark:border-gray-700/60">
                <div className="text-center">
                  <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">
                    {userStats.totalAnalyses}
                  </div>
                  <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Analyses</div>
                </div>
                <div className="text-center border-x border-gray-200/60 dark:border-gray-700/60">
                  <div className="text-3xl font-bold text-green-600 dark:text-green-400">
                    {userStats.avgFormScore}%
                  </div>
                  <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Score</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-orange-600 dark:text-orange-400">
                    {userStats.currentStreak}d
                  </div>
                  <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Streak</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Settings Groups with Enhanced Spacing */}
        {settingsGroups.map((group, groupIndex) => (
          <motion.div
            key={group.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + groupIndex * 0.1 }}
            className="space-y-4"
          >
            {/* Section Header with Divider */}
            <div className="flex items-center space-x-4">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">{group.title}</h3>
              <div className="flex-1 h-px bg-gradient-to-r from-gray-200 to-transparent dark:from-gray-700 dark:to-transparent"></div>
            </div>

            <Card className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm shadow-lg border border-gray-200/50 dark:border-gray-700/50">
              <CardContent className="p-0">
                {group.items.map((item, itemIndex) => (
                  <motion.div
                    key={item.label}
                    whileHover={item.clickable ? { backgroundColor: 'rgba(0,0,0,0.02)' } : {}}
                    className={`flex items-center justify-between p-5 cursor-${
                      item.clickable ? 'pointer' : 'default'
                    } transition-colors ${
                      itemIndex !== group.items.length - 1 ? 'border-b border-gray-200/60 dark:border-gray-700/60' : ''
                    }`}
                    onClick={item.clickable ? item.onClick : undefined}
                  >
                    <div className="flex items-center space-x-4 flex-1">
                      <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center text-gray-600 dark:text-gray-400">
                        {item.icon}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 dark:text-white text-lg">{item.label}</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{item.description}</p>
                        {item.subDescription && (
                          <div className="flex items-center space-x-1 mt-1">
                            <AlertTriangle className="w-3 h-3 text-orange-500" />
                            <p className="text-xs text-orange-600 dark:text-orange-400">{item.subDescription}</p>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="ml-4">{item.action}</div>
                  </motion.div>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        ))}

        {/* Enhanced Logout Button */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
          <Button
            variant="outline"
            size="lg"
            className="w-full text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300 dark:text-red-400 dark:border-red-800 dark:hover:bg-red-900/20 bg-transparent font-semibold py-4 transition-all duration-200"
            onClick={handleLogout}
          >
            <LogOut className="w-5 h-5 mr-3" />
            Sign Out
          </Button>
        </motion.div>
      </div>
    </AppLayout>
  );
}