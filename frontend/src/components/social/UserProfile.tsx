import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Avatar,
  Button,
  Grid,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import {
  Favorite,
  FavoriteBorder,
  Comment,
  Share,
  Edit,
  EmojiEvents,
  People,
} from '@mui/icons-material';
import { User, Achievement, WorkoutShare, socialService } from '../../services/socialService';
import { formatDistanceToNow } from 'date-fns';

interface UserProfileProps {
  userId: string;
  currentUserId: string;
}

export const UserProfile: React.FC<UserProfileProps> = ({ userId, currentUserId }) => {
  const [user, setUser] = useState<User | null>(null);
  const [sharedWorkouts, setSharedWorkouts] = useState<WorkoutShare[]>([]);
  const [isFollowing, setIsFollowing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<Partial<User>>({});
  const [commentDialogOpen, setCommentDialogOpen] = useState(false);
  const [selectedWorkout, setSelectedWorkout] = useState<WorkoutShare | null>(null);
  const [newComment, setNewComment] = useState('');

  useEffect(() => {
    loadUserData();
  }, [userId]);

  const loadUserData = async () => {
    try {
      const userData = await socialService.getUserProfile(userId);
      setUser(userData);
      const workouts = await socialService.getSharedWorkouts(userId);
      setSharedWorkouts(workouts);
    } catch (error) {
      console.error('Failed to load user data:', error);
    }
  };

  const handleFollow = async () => {
    try {
      if (isFollowing) {
        await socialService.unfollowUser(currentUserId, userId);
      } else {
        await socialService.followUser(currentUserId, userId);
      }
      setIsFollowing(!isFollowing);
      loadUserData();
    } catch (error) {
      console.error('Failed to update follow status:', error);
    }
  };

  const handleLike = async (workoutId: string) => {
    try {
      await socialService.likeWorkoutShare(workoutId, currentUserId);
      loadUserData();
    } catch (error) {
      console.error('Failed to like workout:', error);
    }
  };

  const handleComment = async (workoutId: string) => {
    try {
      await socialService.addComment(workoutId, currentUserId, newComment);
      setNewComment('');
      setCommentDialogOpen(false);
      loadUserData();
    } catch (error) {
      console.error('Failed to add comment:', error);
    }
  };

  const handleEdit = async () => {
    try {
      await socialService.updateUserProfile(userId, editForm);
      setIsEditing(false);
      loadUserData();
    } catch (error) {
      console.error('Failed to update profile:', error);
    }
  };

  if (!user) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Box sx={{ maxWidth: 800, margin: '0 auto', padding: 3 }}>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <Avatar
              src={user.avatar}
              sx={{ width: 100, height: 100, mr: 2 }}
            />
            <Box sx={{ flex: 1 }}>
              <Typography variant="h4">{user.username}</Typography>
              <Typography variant="body1" color="text.secondary">
                {user.bio || 'No bio yet'}
              </Typography>
              <Box sx={{ mt: 1 }}>
                <Chip
                  label={user.fitnessLevel}
                  color="primary"
                  size="small"
                  sx={{ mr: 1 }}
                />
                <Chip
                  icon={<People />}
                  label={`${user.followers} followers`}
                  size="small"
                  sx={{ mr: 1 }}
                />
                <Chip
                  icon={<EmojiEvents />}
                  label={`${user.achievements.length} achievements`}
                  size="small"
                />
              </Box>
            </Box>
            {userId === currentUserId ? (
              <IconButton onClick={() => setIsEditing(true)}>
                <Edit />
              </IconButton>
            ) : (
              <Button
                variant={isFollowing ? 'outlined' : 'contained'}
                onClick={handleFollow}
              >
                {isFollowing ? 'Unfollow' : 'Follow'}
              </Button>
            )}
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Achievements
          </Typography>
          <Grid container spacing={2}>
            {user.achievements.map((achievement) => (
              <Grid item xs={12} sm={6} md={4} key={achievement.id}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Avatar sx={{ mr: 2 }}>{achievement.icon}</Avatar>
                      <Box>
                        <Typography variant="subtitle1">{achievement.name}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {achievement.description}
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Shared Workouts
          </Typography>
          <List>
            {sharedWorkouts.map((workout) => (
              <React.Fragment key={workout.id}>
                <ListItem
                  alignItems="flex-start"
                  secondaryAction={
                    <Box>
                      <IconButton onClick={() => handleLike(workout.id)}>
                        {workout.likes > 0 ? <Favorite color="error" /> : <FavoriteBorder />}
                      </IconButton>
                      <IconButton onClick={() => {
                        setSelectedWorkout(workout);
                        setCommentDialogOpen(true);
                      }}>
                        <Comment />
                      </IconButton>
                      <IconButton>
                        <Share />
                      </IconButton>
                    </Box>
                  }
                >
                  <ListItemText
                    primary={workout.template.name}
                    secondary={
                      <>
                        <Typography component="span" variant="body2" color="text.primary">
                          {workout.template.description}
                        </Typography>
                        <br />
                        <Typography variant="caption" color="text.secondary">
                          {formatDistanceToNow(new Date(workout.createdAt), { addSuffix: true })}
                        </Typography>
                      </>
                    }
                  />
                </ListItem>
                <Divider variant="inset" component="li" />
              </React.Fragment>
            ))}
          </List>
        </CardContent>
      </Card>

      <Dialog open={isEditing} onClose={() => setIsEditing(false)}>
        <DialogTitle>Edit Profile</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Bio"
            fullWidth
            multiline
            rows={4}
            value={editForm.bio || ''}
            onChange={(e) => setEditForm({ ...editForm, bio: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Fitness Level"
            select
            fullWidth
            value={editForm.fitnessLevel || user.fitnessLevel}
            onChange={(e) => setEditForm({ ...editForm, fitnessLevel: e.target.value as User['fitnessLevel'] })}
            SelectProps={{
              native: true,
            }}
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsEditing(false)}>Cancel</Button>
          <Button onClick={handleEdit} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={commentDialogOpen} onClose={() => setCommentDialogOpen(false)}>
        <DialogTitle>Add Comment</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Comment"
            fullWidth
            multiline
            rows={4}
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCommentDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => selectedWorkout && handleComment(selectedWorkout.id)}
            variant="contained"
          >
            Post
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}; 