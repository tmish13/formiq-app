import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield,
  HelpCircle,
  LogOut,
  Edit3,
  Camera,
  Moon,
  MessageSquare,
  Smartphone,
  RotateCcw,
  ChevronRight,
  AlertTriangle,
  X,
  Check,
  Loader2,
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../hooks/use-toast';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import { setUser } from '../store/slices/authSlice';
import { progressService } from '../services/progressService';
import { useAuth } from '../hooks/useAuth';
import apiService from '../services/apiService';
import AppLayout from '../components/layout/AppLayout';
import { logBetaEvent, getBetaStats } from '../utils/logEvent';
import { getUserPrefs, setUserPrefs, type UserPrefs } from '../utils/userPrefs';

interface UserStats {
  totalAnalyses: number;
  avgFormScore: number;
  currentStreak: number;
  joinDate: string;
}

const FITNESS_LEVELS = ['beginner', 'intermediate', 'advanced'] as const;

export default function ProfilePage() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { toast } = useToast();
  const user = useSelector((state: RootState) => state.auth.user);
  const { updateProfile, logout, changePassword } = useAuth();

  const [darkMode, setDarkMode] = useState(false);
  const [, setNotifications] = useState(true);
  const [autoRecord, setAutoRecord] = useState(false);
  const [userStats, setUserStats] = useState<UserStats>({
    totalAnalyses: 0,
    avgFormScore: 0,
    currentStreak: 0,
    joinDate: 'January 2024',
  });
  const [, setLoading] = useState(false);

  // Edit Profile modal state
  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState({ full_name: '', fitness_level: '' });
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState('');

  // Extended profile (localStorage)
  const [extProfile, setExtProfile] = useState<UserPrefs>(() => getUserPrefs());

  // Change Password modal state
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
  const [passwordForm, setPasswordForm] = useState({ current: '', newPass: '', confirm: '' });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  // Avatar upload state
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);

  // Beta feedback modal state
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackForm, setFeedbackForm] = useState({ category: '', message: '', score: '', exercise: '' });
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);

  // Beta diagnostics panel state (hidden — tap version 5×)
  const [, setVersionTapCount] = useState(0);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  useEffect(() => {
    loadUserData();
    loadPreferences();
    apiService.getUserSettings()
      .then(res => {
        const val = res.data?.notifications?.workout_reminders;
        if (val !== undefined) setNotifications(val);
      })
      .catch(() => {}); // keep localStorage default on failure
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (user) {
      setEditForm({
        full_name: user.full_name || '',
        fitness_level: user.fitness_level || '',
      });
    }
  }, [user]);

  const loadUserData = async () => {
    try {
      const progressOverview = await progressService.getProgressOverview();
      setUserStats({
        totalAnalyses: progressOverview.totalSessions,
        avgFormScore: Math.round(progressOverview.averageScore),
        currentStreak: progressOverview.currentStreak,
        joinDate: user?.created_at
          ? new Date(user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
          : 'January 2024',
      });
    } catch (error) {
      console.error('Failed to load user stats:', error);
      toast({
        title: "Couldn't load stats",
        description: "We couldn't load your profile stats right now.",
        duration: 3000,
      });
      setUserStats({
        totalAnalyses: 0,
        avgFormScore: 0,
        currentStreak: 0,
        joinDate: user?.created_at
          ? new Date(user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
          : 'January 2024',
      });
    } finally {
      setLoading(false);
    }
  };

  const loadPreferences = () => {
    const savedTheme = localStorage.getItem('formiq-theme');
    if (savedTheme === 'dark') {
      setDarkMode(true);
      document.documentElement.classList.add('dark');
    }
    const savedNotifications = localStorage.getItem('formiq-notifications');
    if (savedNotifications !== null) setNotifications(JSON.parse(savedNotifications));
    const savedAutoRecord = localStorage.getItem('formiq-auto-record');
    if (savedAutoRecord !== null) setAutoRecord(JSON.parse(savedAutoRecord));
  };

  const handleThemeToggle = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('formiq-theme', 'dark');
      toast({ title: 'Dark Mode Enabled', description: 'Interface switched to dark theme', duration: 2000 });
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('formiq-theme', 'light');
      toast({ title: 'Light Mode Enabled', description: 'Interface switched to light theme', duration: 2000 });
    }
  };

  const handleAutoRecordToggle = () => {
    const next = !autoRecord;
    setAutoRecord(next);
    localStorage.setItem('formiq-auto-record', JSON.stringify(next));
    toast({
      title: next ? 'Auto-Record Enabled' : 'Auto-Record Disabled',
      description: next ? 'Recording will start automatically' : 'Manual recording required',
      duration: 2000,
    });
  };

  // ─── Change Password ──────────────────────────────────────────────────────────

  const handleChangePassword = async () => {
    setPasswordError('');
    if (!passwordForm.current || !passwordForm.newPass) {
      setPasswordError('All fields are required.');
      return;
    }
    if (passwordForm.newPass !== passwordForm.confirm) {
      setPasswordError('New passwords do not match.');
      return;
    }
    setPasswordSaving(true);
    try {
      await changePassword(passwordForm.current, passwordForm.newPass);
      setShowChangePasswordModal(false);
      setPasswordForm({ current: '', newPass: '', confirm: '' });
      toast({ title: 'Password updated successfully.', duration: 2500 });
    } catch (err: any) {
      if (err?.status === 400) {
        setPasswordError('Current password is incorrect.');
      } else {
        setPasswordError('Something went wrong updating your password. Please try again.');
      }
    } finally {
      setPasswordSaving(false);
    }
  };

  // ─── Edit Profile ────────────────────────────────────────────────────────────

  const openEditModal = () => {
    setEditForm({ full_name: user?.full_name || '', fitness_level: user?.fitness_level || '' });
    setExtProfile(getUserPrefs());
    setEditError('');
    setShowEditModal(true);
  };

  const handleEditSave = async () => {
    setEditSaving(true);
    setEditError('');
    try {
      await updateProfile({
        full_name: editForm.full_name.trim() || undefined,
        fitness_level: editForm.fitness_level || undefined,
        weight_kg: extProfile.weightKg ?? undefined,
        age: extProfile.age ?? undefined,
        height_cm: extProfile.heightCm ?? undefined,
        training_experience: extProfile.trainingExperience ?? undefined,
      } as any);
      setUserPrefs(extProfile);
      setShowEditModal(false);
      toast({ title: 'Profile updated', description: 'Your changes have been saved.', duration: 2500 });
    } catch (err: any) {
      setEditError(err.message || 'Save failed. Please try again.');
    } finally {
      setEditSaving(false);
    }
  };

  // ─── Avatar Upload ────────────────────────────────────────────────────────────

  const handleAvatarClick = () => {
    avatarInputRef.current?.click();
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowed = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
    if (!allowed.includes(file.type)) {
      toast({ title: 'Invalid file type', description: 'Only JPG, PNG, and GIF are supported.', duration: 3000 });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast({ title: 'File too large', description: 'Maximum size is 5 MB.', duration: 3000 });
      return;
    }

    setAvatarUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await apiService.updateAvatar(formData);
      const { avatar_url } = response.data;
      if (user) dispatch(setUser({ ...user, profile_image_url: avatar_url }));
      toast({ title: 'Avatar updated', description: 'Your profile photo has been saved.', duration: 2500 });
    } catch (err: any) {
      toast({ title: 'Upload failed', description: err.message || 'Please try again.', duration: 3000 });
    } finally {
      setAvatarUploading(false);
      if (avatarInputRef.current) avatarInputRef.current.value = '';
    }
  };

  // ─── Other handlers ───────────────────────────────────────────────────────────

  const resetApp = async () => {
    try {
      await updateProfile({ has_completed_onboarding: false });
      navigate('/onboarding?replay=true');
    } catch {
      toast({ title: 'Could not replay onboarding. Please try again later.', duration: 3000 });
    }
  };

  const handleLogout = async () => {
    toast({ title: 'Signed Out', description: "You've been successfully signed out", duration: 2000 });
    await logout();
  };

  // ─── Beta Feedback ───────────────────────────────────────────────────────

  const handleSubmitFeedback = async () => {
    if (!feedbackForm.message.trim()) return;
    setFeedbackSubmitting(true);
    const payload = {
      user_id: user?.id,
      category: feedbackForm.category || 'General',
      message: feedbackForm.message,
      score: feedbackForm.score ? parseFloat(feedbackForm.score) : undefined,
      exercise: feedbackForm.exercise || undefined,
      timestamp: new Date().toISOString(),
    };
    try {
      const token = localStorage.getItem('formiq_auth_token');
      const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
      const resp = await fetch(`${baseUrl}/beta-feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error('not wired');
    } catch {
      console.log('BETA_FEEDBACK', payload);
    }
    toast({ title: 'Feedback received — thank you!', duration: 2500 });
    setShowFeedbackModal(false);
    setFeedbackForm({ category: '', message: '', score: '', exercise: '' });
    setFeedbackSubmitting(false);
  };

  // ─── Version tap (hidden diagnostics) ────────────────────────────────────

  const handleVersionTap = () => {
    setVersionTapCount(c => {
      const next = c + 1;
      if (next >= 5) {
        setShowDiagnostics(true);
        return 0;
      }
      return next;
    });
  };

  // ─── Display helpers ──────────────────────────────────────────────────────────

  const displayName = user?.full_name || user?.email?.split('@')[0] || 'User';
  const avatarInitial = (user?.full_name?.[0] || user?.email?.[0] || 'U').toUpperCase();
  const hasStats = userStats.totalAnalyses > 0;

  const settingsGroups = [
    {
      title: 'Preferences',
      items: [
        {
          icon: <Moon className="w-4 h-4" />,
          label: 'Dark Mode',
          description: 'Switch between light and dark themes',
          action: (
            <Switch
              checked={darkMode}
              onCheckedChange={handleThemeToggle}
              className="ml-auto data-[state=checked]:bg-violet-500"
            />
          ),
          clickable: true,
          onClick: handleThemeToggle,
        },
        {
          icon: <Smartphone className="w-4 h-4" />,
          label: 'Auto-Record',
          description: "Start recording automatically when you're in position",
          action: (
            <Switch
              checked={autoRecord}
              onCheckedChange={handleAutoRecordToggle}
              className="ml-auto data-[state=checked]:bg-violet-500"
            />
          ),
          clickable: true,
          onClick: handleAutoRecordToggle,
        },
      ],
    },
    {
      title: 'Account',
      items: [
        {
          icon: <Edit3 className="w-4 h-4" />,
          label: 'Edit Profile',
          description: 'Update your name and fitness level',
          action: <ChevronRight className="w-4 h-4 text-muted-foreground" />,
          clickable: true,
          onClick: openEditModal,
        },
        {
          icon: <Shield className="w-4 h-4" />,
          label: 'Privacy & Security',
          description: 'Change your password. Your videos are stored securely and used only to improve your form.',
          action: <ChevronRight className="w-4 h-4 text-muted-foreground" />,
          clickable: true,
          onClick: () => { setPasswordError(''); setShowChangePasswordModal(true); },
        },
      ],
    },
    {
      title: 'Support',
      items: [
        {
          icon: <MessageSquare className="w-4 h-4" />,
          label: 'Beta Feedback',
          description: 'Report a bug, scoring issue, or share a suggestion',
          action: <ChevronRight className="w-4 h-4 text-muted-foreground" />,
          clickable: true,
          onClick: () => {
            logBetaEvent('feedback_opened');
            setShowFeedbackModal(true);
          },
        },
        {
          icon: <HelpCircle className="w-4 h-4" />,
          label: 'Help & Support',
          description: 'Get help and contact support',
          action: <ChevronRight className="w-4 h-4 text-muted-foreground" />,
          clickable: true,
          onClick: () => {
            window.open('mailto:support@formiq.ai?subject=FormIQ%20Help%20Request', '_blank');
          },
        },
        {
          icon: <RotateCcw className="w-4 h-4" />,
          label: 'Edit Training Profile',
          description: 'Update your fitness goal, experience level, and preferences',
          subDescription: 'You stay signed in — your data is not affected',
          action: (
            <Button
              variant="ghost"
              size="sm"
              onClick={resetApp}
              className="text-purple-400 hover:text-purple-300 hover:bg-purple-900/20 hover:underline h-8 text-xs"
            >
              Edit
            </Button>
          ),
          clickable: false,
        },
      ],
    },
  ];

  return (
    <AppLayout>
      {/* Hidden file input for avatar */}
      <input
        ref={avatarInputRef}
        type="file"
        accept="image/jpeg,image/jpg,image/png,image/gif"
        className="hidden"
        onChange={handleAvatarChange}
      />

      <div className="px-4 py-5 space-y-5 max-w-4xl mx-auto" style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 96px)' }}>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-foreground">Profile</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage your account and preferences</p>
        </motion.div>

        {/* Profile Card */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <Card className="border border-slate-700/80 bg-gradient-to-br from-slate-900 to-slate-800 shadow-lg shadow-black/30 rounded-2xl overflow-hidden">
            <CardContent className="p-5">
              <div className="flex items-center gap-4 mb-5">
                <div className="relative">
                  <Avatar className="w-16 h-16">
                    <AvatarImage src={user?.profile_image_url || ''} />
                    <AvatarFallback className="bg-gradient-to-br from-violet-600 to-purple-700 text-white text-lg font-bold">
                      {avatarInitial}
                    </AvatarFallback>
                  </Avatar>
                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    disabled={avatarUploading}
                    className="absolute -bottom-0.5 -right-0.5 w-6 h-6 bg-violet-600 rounded-full flex items-center justify-center text-white shadow-sm hover:bg-violet-700 transition-colors disabled:opacity-60"
                    onClick={handleAvatarClick}
                  >
                    {avatarUploading
                      ? <Loader2 className="w-3 h-3 animate-spin" />
                      : <Camera className="w-3 h-3" />}
                  </motion.button>
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-lg font-bold text-white">{displayName}</h2>
                  <p className="text-sm text-slate-400">{user?.email || ''}</p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    {/* Beta badge — subtle, lower contrast */}
                    <span className="inline-flex items-center text-[10px] px-2 py-0.5 bg-slate-800/80 text-slate-400 border border-slate-600/60 rounded-full">
                      Beta Access
                    </span>
                    {/* Fitness level badge — more prominent with purple accent */}
                    {user?.fitness_level && (
                      <span className="inline-flex items-center text-xs px-2.5 py-0.5 bg-purple-700/80 text-white rounded-full capitalize font-medium">
                        {user.fitness_level}
                      </span>
                    )}
                    <span className="text-[10px] text-slate-500">Since {userStats.joinDate}</span>
                  </div>
                  {user?.fitness_goal && (
                    <p className="text-xs text-slate-400 mt-1.5">
                      Goal: <span className="font-medium text-slate-200">{user.fitness_goal}</span>
                    </p>
                  )}
                </div>
              </div>

              {/* Stats — Avg Score is the hero stat */}
              {hasStats ? (
                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-700/60">
                  <div className="text-center space-y-0.5">
                    <div className="text-lg font-bold text-slate-200">{userStats.totalAnalyses}</div>
                    <div className="text-[11px] text-slate-500">Analyses</div>
                  </div>
                  <div className="text-center border-x border-slate-700/60 space-y-0.5">
                    <div className="text-2xl font-bold text-violet-300">{userStats.avgFormScore}%</div>
                    <div className="text-[11px] text-slate-400 font-medium">Avg Score</div>
                  </div>
                  <div className="text-center space-y-0.5">
                    <div className="text-lg font-bold text-slate-200">{userStats.currentStreak}d</div>
                    <div className="text-[11px] text-slate-500">Streak</div>
                  </div>
                </div>
              ) : (
                <div className="pt-4 border-t border-slate-700/60 text-center">
                  <p className="text-xs text-slate-500">
                    Complete your first analysis to see your stats here.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Settings Groups */}
        {settingsGroups.map((group, groupIndex) => (
          <motion.div
            key={group.title}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + groupIndex * 0.05 }}
            className="space-y-1.5"
          >
            <h3 className={`text-xs font-semibold uppercase tracking-[0.18em] px-1 ${
              group.title === 'Account' ? 'text-slate-300' : 'text-muted-foreground'
            }`}>
              {group.title}
            </h3>

            <Card className="border border-border bg-card rounded-xl overflow-hidden">
              <CardContent className="p-0">
                {group.items.map((item, itemIndex) => (
                  <div
                    key={item.label}
                    className={`flex items-center justify-between px-4 py-3 ${
                      item.clickable
                        ? 'cursor-pointer hover:bg-slate-800/60 active:bg-slate-900/70'
                        : ''
                    } transition-colors duration-150 ease-out ${
                      itemIndex !== group.items.length - 1 ? 'border-b border-border' : ''
                    }`}
                    onClick={item.clickable ? item.onClick : undefined}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {/* Icon container — accent when Dark Mode is ON */}
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors ${
                        item.label === 'Dark Mode' && darkMode
                          ? 'bg-violet-500/20 text-violet-300'
                          : 'bg-muted text-muted-foreground'
                      }`}>
                        {item.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <h4 className="text-sm font-medium text-foreground">{item.label}</h4>
                          {/* "On" pill for Dark Mode active state */}
                          {item.label === 'Dark Mode' && darkMode && (
                            <span className="inline-flex items-center bg-violet-500/20 text-violet-300 text-[10px] px-1.5 py-0.5 rounded-full leading-none">
                              On
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{item.description}</p>
                        {item.subDescription && (
                          <div className="flex items-center gap-1 mt-0.5">
                            <AlertTriangle className="w-3 h-3 text-amber-400/70 flex-shrink-0" />
                            <p className="text-[11px] text-amber-300/80">{item.subDescription}</p>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">{item.action}</div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        ))}

        {/* Notifications */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.27 }}>
          <div className="rounded-xl border px-4 py-4 space-y-3">
            <h3 className="text-sm font-semibold">Notifications</h3>

            {[
              "Workout reminders",
              "Analysis results ready",
              "Weekly progress summary",
            ].map((label) => (
              <div key={label} className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{label}</span>
                <span className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wide">Coming soon</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Help & Feedback */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.28 }}>
          <div className="rounded-xl border px-4 py-4 space-y-2">
            <h3 className="text-sm font-semibold">Help & Feedback</h3>

            {[
              { label: "Report a bug", subject: "Bug Report" },
              { label: "Suggest an exercise", subject: "Exercise Suggestion" },
              { label: "General feedback", subject: "Feedback" },
            ].map(({ label, subject }) => (
              <button
                key={subject}
                type="button"
                onClick={() =>
                  (window.location.href = `mailto:support@formiq.com?subject=${encodeURIComponent(subject)}`)
                }
                className="w-full flex items-center justify-between rounded-lg border px-3 py-2.5 text-sm text-left hover:bg-muted/50 transition-colors"
              >
                {label}
                <span className="text-muted-foreground text-xs">→</span>
              </button>
            ))}
          </div>
        </motion.div>

        {/* Sign Out — refined destructive button */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 bg-red-900/30 border border-red-600/60 text-red-300 rounded-xl py-3.5 font-semibold text-sm hover:bg-red-800/50 active:bg-red-900/80 transition-all duration-150"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </motion.div>

        {/* Version info — tap 5× to unlock diagnostics panel */}
        <div className="text-center pt-2 pb-4">
          <p
            className="text-[11px] text-muted-foreground/50 cursor-default select-none"
            onClick={handleVersionTap}
          >
            Version 0.9.0-beta
          </p>
        </div>

      </div>

      {/* Change Password Modal */}
      <AnimatePresence>
        {showChangePasswordModal && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => { setShowChangePasswordModal(false); setPasswordForm({ current: '', newPass: '', confirm: '' }); setPasswordError(''); }}
            />
            <motion.div
              className="relative bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700/80 rounded-2xl shadow-2xl w-full max-w-md p-6"
              initial={{ scale: 0.92, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.92, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-white">Change Password</h2>
                <button
                  onClick={() => { setShowChangePasswordModal(false); setPasswordForm({ current: '', newPass: '', confirm: '' }); setPasswordError(''); }}
                  className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-700/60 transition-colors"
                >
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Current Password</label>
                  <input
                    type="password"
                    value={passwordForm.current}
                    onChange={e => setPasswordForm(f => ({ ...f, current: e.target.value }))}
                    placeholder="Enter current password"
                    className="w-full px-4 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">New Password</label>
                  <input
                    type="password"
                    value={passwordForm.newPass}
                    onChange={e => setPasswordForm(f => ({ ...f, newPass: e.target.value }))}
                    placeholder="Enter new password"
                    className="w-full px-4 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm New Password</label>
                  <input
                    type="password"
                    value={passwordForm.confirm}
                    onChange={e => setPasswordForm(f => ({ ...f, confirm: e.target.value }))}
                    placeholder="Confirm new password"
                    className="w-full px-4 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition"
                  />
                </div>
                {passwordError && (
                  <p className="text-sm text-red-400">{passwordError}</p>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => { setShowChangePasswordModal(false); setPasswordForm({ current: '', newPass: '', confirm: '' }); setPasswordError(''); }}
                  disabled={passwordSaving}
                  className="flex-1 px-4 py-2.5 border border-slate-600/60 text-slate-300 rounded-lg hover:bg-slate-700/40 transition-colors text-sm font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleChangePassword}
                  disabled={passwordSaving}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-lg transition-all text-sm font-medium disabled:opacity-60"
                >
                  {passwordSaving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Shield className="w-4 h-4" />
                  )}
                  {passwordSaving ? 'Updating…' : 'Update Password'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Beta Feedback Modal */}
      <AnimatePresence>
        {showFeedbackModal && (
          <motion.div
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setShowFeedbackModal(false)}
            />
            <motion.div
              className="relative bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700/80 rounded-2xl shadow-2xl w-full max-w-md p-6"
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 28 }}
            >
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="text-lg font-bold text-white">Beta Feedback</h2>
                  <p className="text-xs text-slate-400 mt-0.5">Help us improve FormIQ</p>
                </div>
                <button
                  onClick={() => setShowFeedbackModal(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-700/60 transition-colors"
                >
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>

              <div className="space-y-4">
                {/* Category */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Category</label>
                  <select
                    value={feedbackForm.category}
                    onChange={e => setFeedbackForm(f => ({ ...f, category: e.target.value }))}
                    className="w-full px-3 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition text-sm"
                  >
                    <option value="">Select category…</option>
                    <option value="Recording issue">Recording issue</option>
                    <option value="Scoring seems inaccurate">Scoring seems inaccurate</option>
                    <option value="Snapshot missing">Snapshot missing</option>
                    <option value="UI bug">UI bug</option>
                    <option value="Suggestion">Suggestion</option>
                  </select>
                </div>

                {/* Message */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Message <span className="text-red-400">*</span>
                  </label>
                  <textarea
                    value={feedbackForm.message}
                    onChange={e => setFeedbackForm(f => ({ ...f, message: e.target.value }))}
                    placeholder="Describe what happened or what you'd like to see improved…"
                    rows={4}
                    className="w-full px-3 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition text-sm resize-none"
                  />
                </div>

                {/* Optional: score + exercise */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Score received (optional)</label>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={feedbackForm.score}
                      onChange={e => setFeedbackForm(f => ({ ...f, score: e.target.value }))}
                      placeholder="e.g. 72"
                      className="w-full px-3 py-2 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 outline-none transition text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Exercise (optional)</label>
                    <input
                      type="text"
                      value={feedbackForm.exercise}
                      onChange={e => setFeedbackForm(f => ({ ...f, exercise: e.target.value }))}
                      placeholder="e.g. squat"
                      className="w-full px-3 py-2 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 outline-none transition text-sm"
                    />
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-5">
                <button
                  onClick={() => setShowFeedbackModal(false)}
                  disabled={feedbackSubmitting}
                  className="flex-1 px-4 py-2.5 border border-slate-600/60 text-slate-300 rounded-lg hover:bg-slate-700/40 transition-colors text-sm font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmitFeedback}
                  disabled={feedbackSubmitting || !feedbackForm.message.trim()}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-lg transition-all text-sm font-medium disabled:opacity-50"
                >
                  {feedbackSubmitting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <MessageSquare className="w-4 h-4" />
                  )}
                  {feedbackSubmitting ? 'Sending…' : 'Send Feedback'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Beta Diagnostics Panel (hidden — tap version 5×) */}
      <AnimatePresence>
        {showDiagnostics && (() => {
          const stats = getBetaStats();
          const snapshotRate =
            stats.analysis_success > 0
              ? `${Math.round((1 - stats.snapshot_missing / stats.analysis_success) * 100)}%`
              : 'N/A';
          const lastAnalysis = stats.last_analysis_at
            ? new Date(stats.last_analysis_at).toLocaleString()
            : 'No data';
          const rows: [string, string][] = [
            ['User ID', user?.id?.toString() ?? 'Unknown'],
            ['Total analyses', String(userStats.totalAnalyses)],
            ['Analyses succeeded', String(stats.analysis_success)],
            ['Analyses failed', String(stats.analysis_failed)],
            ['Invalid clips detected', String(stats.invalid_clip_detected)],
            ['Snapshot success rate', snapshotRate],
            ['Last analysis', lastAnalysis],
          ];
          return (
            <motion.div
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onClick={() => setShowDiagnostics(false)}
              />
              <motion.div
                className="relative bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700/80 rounded-2xl shadow-2xl w-full max-w-sm p-5"
                initial={{ scale: 0.92, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.92, opacity: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-base font-bold text-white">Beta Diagnostics</h2>
                    <p className="text-[11px] text-slate-500 mt-0.5">Client-only — not sent anywhere</p>
                  </div>
                  <button
                    onClick={() => setShowDiagnostics(false)}
                    className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-slate-700/60 transition-colors"
                  >
                    <X className="w-3.5 h-3.5 text-slate-400" />
                  </button>
                </div>
                <div className="space-y-2">
                  {rows.map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between py-1 border-b border-slate-700/40 last:border-0">
                      <span className="text-xs text-slate-400">{label}</span>
                      <span className="text-xs font-mono text-slate-200 text-right max-w-[55%] truncate">{value}</span>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setShowDiagnostics(false)}
                  className="w-full mt-4 py-2 bg-slate-700/60 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition-colors"
                >
                  Close
                </button>
              </motion.div>
            </motion.div>
          );
        })()}
      </AnimatePresence>

      {/* Edit Profile Modal */}
      <AnimatePresence>
        {showEditModal && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setShowEditModal(false)}
            />
            <motion.div
              className="relative bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700/80 rounded-2xl shadow-2xl w-full max-w-md p-6"
              initial={{ scale: 0.92, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.92, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-white">Edit Profile</h2>
                <button
                  onClick={() => setShowEditModal(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-700/60 transition-colors"
                >
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Full Name</label>
                  <input
                    type="text"
                    value={editForm.full_name}
                    onChange={e => setEditForm(f => ({ ...f, full_name: e.target.value }))}
                    placeholder="Your full name"
                    className="w-full px-4 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Fitness Level</label>
                  <select
                    value={editForm.fitness_level}
                    onChange={e => setEditForm(f => ({ ...f, fitness_level: e.target.value }))}
                    className="w-full px-4 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition"
                  >
                    <option value="">Select level…</option>
                    {FITNESS_LEVELS.map(l => (
                      <option key={l} value={l} className="capitalize bg-slate-800">
                        {l.charAt(0).toUpperCase() + l.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Height */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Height (cm) — optional
                  </label>
                  <input
                    type="number"
                    placeholder="e.g. 178"
                    value={extProfile.heightCm ?? ""}
                    onChange={(e) => setExtProfile((p) => ({ ...p, heightCm: parseInt(e.target.value) || undefined }))}
                    className="w-full px-4 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition"
                  />
                </div>

                {/* Body weight */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Body weight (kg) — optional
                  </label>
                  <input
                    type="number"
                    placeholder="e.g. 82"
                    value={extProfile.weightKg ?? ""}
                    onChange={(e) => setExtProfile((p) => ({ ...p, weightKg: parseFloat(e.target.value) || undefined }))}
                    className="w-full px-4 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition"
                  />
                </div>

                {/* Age */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Age — optional
                  </label>
                  <input
                    type="number"
                    placeholder="e.g. 28"
                    min={13}
                    max={100}
                    value={extProfile.age ?? ""}
                    onChange={(e) => setExtProfile((p) => ({ ...p, age: parseInt(e.target.value) || undefined }))}
                    className="w-full px-4 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition"
                  />
                </div>

                {/* Training experience */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Training experience
                  </label>
                  <div className="flex gap-2 flex-wrap">
                    {(["beginner", "intermediate", "advanced", "athlete"] as const).map((lvl) => (
                      <button
                        key={lvl}
                        type="button"
                        onClick={() => setExtProfile((p) => ({ ...p, trainingExperience: lvl }))}
                        className={`rounded-full border px-3 py-1 text-xs capitalize transition-colors ${
                          extProfile.trainingExperience === lvl
                            ? "border-violet-500 bg-violet-600 text-white"
                            : "border-slate-600 hover:bg-slate-700/50 text-slate-300"
                        }`}
                      >
                        {lvl}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Injuries */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Injuries or limitations — optional
                  </label>
                  <input
                    placeholder="e.g. Right knee, lower back"
                    value={extProfile.injuries ?? ""}
                    onChange={(e) => setExtProfile((p) => ({ ...p, injuries: e.target.value }))}
                    className="w-full px-4 py-2.5 border border-slate-700/60 rounded-lg bg-slate-800/60 text-white placeholder:text-slate-500 focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 outline-none transition"
                  />
                </div>

                {editError && (
                  <p className="text-sm text-red-400">{editError}</p>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowEditModal(false)}
                  disabled={editSaving}
                  className="flex-1 px-4 py-2.5 border border-slate-600/60 text-slate-300 rounded-lg hover:bg-slate-700/40 transition-colors text-sm font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleEditSave}
                  disabled={editSaving}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-lg transition-all text-sm font-medium disabled:opacity-60"
                >
                  {editSaving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  {editSaving ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </AppLayout>
  );
}
