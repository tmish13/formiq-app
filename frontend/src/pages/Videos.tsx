import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Container,
  Grid,
  Card,
  CardMedia,
  CardContent,
  CardActions,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  CircularProgress,
  Stack,
  Chip,
  IconButton,
  useTheme,
  Divider,
  Alert,
  Tooltip
} from '@mui/material';
import {
  Delete as DeleteIcon,
  PlayArrow as PlayArrowIcon,
  Refresh as RefreshIcon,
  CloudUpload as CloudUploadIcon,
  VideoLibrary as VideoLibraryIcon,
  SortByAlpha as SortIcon
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import VideoUpload from '../components/VideoUpload';
import { videoService, Video, VideoStatus } from '../services/videos';
import { useInterval } from '../hooks/useInterval';

const statusColors = {
  [VideoStatus.PENDING]: 'warning',
  [VideoStatus.PROCESSING]: 'info',
  [VideoStatus.READY]: 'success',
  [VideoStatus.FAILED]: 'error',
  [VideoStatus.DELETED]: 'default',
};

const statusLabels = {
  [VideoStatus.PENDING]: 'Pending',
  [VideoStatus.PROCESSING]: 'Processing',
  [VideoStatus.READY]: 'Ready',
  [VideoStatus.FAILED]: 'Failed',
  [VideoStatus.DELETED]: 'Deleted',
};

const VideosPage: React.FC = () => {
  const theme = useTheme();
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [pollingEnabled, setPollingEnabled] = useState(false);

  const fetchVideos = async () => {
    try {
      setLoading(true);
      setError(null);
      const fetchedVideos = await videoService.listVideos();
      setVideos(fetchedVideos);
      
      // Enable polling if there are any videos in pending or processing state
      const hasProcessingVideos = fetchedVideos.some(
        video => video.status === VideoStatus.PENDING || video.status === VideoStatus.PROCESSING
      );
      setPollingEnabled(hasProcessingVideos);
    } catch (err) {
      setError('Failed to load videos. Please try again.');
      console.error('Error fetching videos:', err);
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchVideos();
  }, []);

  // Set up polling for pending/processing videos
  useInterval(
    () => {
      // Only fetch if not already loading and polling is enabled
      if (!loading && pollingEnabled) {
        fetchVideos();
      }
    },
    pollingEnabled ? 5000 : null // Poll every 5 seconds if enabled, null to disable
  );

  const handleDeleteVideo = async (videoId: string) => {
    if (!window.confirm('Are you sure you want to delete this video?')) {
      return;
    }
    
    try {
      await videoService.deleteVideo(videoId);
      setVideos(videos.filter(video => video.id !== videoId));
    } catch (err) {
      setError('Failed to delete video. Please try again.');
      console.error('Error deleting video:', err);
    }
  };

  const handleUploadComplete = (video: Video) => {
    setVideos(prevVideos => [video, ...prevVideos]);
    setUploadDialogOpen(false);
  };

  const handlePreviewClick = (video: Video) => {
    setSelectedVideo(video);
    setPreviewDialogOpen(true);
  };

  const toggleSortOrder = () => {
    setSortOrder(prevOrder => (prevOrder === 'asc' ? 'desc' : 'asc'));
  };

  const sortedVideos = [...videos].sort((a, b) => {
    const dateA = new Date(a.created_at).getTime();
    const dateB = new Date(b.created_at).getTime();
    return sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
  });

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1" gutterBottom>
          <VideoLibraryIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
          My Videos
        </Typography>
        
        <Stack direction="row" spacing={2}>
          <Tooltip title={`Sort by ${sortOrder === 'asc' ? 'oldest' : 'newest'} first`}>
            <Button 
              variant="outlined"
              startIcon={<SortIcon />}
              onClick={toggleSortOrder}
            >
              {sortOrder === 'asc' ? 'Oldest first' : 'Newest first'}
            </Button>
          </Tooltip>
          
          <Button
            variant="contained"
            color="primary"
            startIcon={<CloudUploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
          >
            Upload Video
          </Button>
          
          <IconButton 
            color="primary" 
            onClick={fetchVideos}
            disabled={loading}
          >
            <RefreshIcon />
          </IconButton>
        </Stack>
      </Box>
      
      {error && (
        <Alert 
          severity="error" 
          sx={{ mb: 3 }}
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}
      
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
          <CircularProgress />
        </Box>
      ) : sortedVideos.length === 0 ? (
        <Box 
          display="flex" 
          flexDirection="column" 
          justifyContent="center" 
          alignItems="center" 
          minHeight="300px"
          sx={{ backgroundColor: theme.palette.background.default, borderRadius: 2, p: 4 }}
        >
          <VideoLibraryIcon sx={{ fontSize: 60, color: theme.palette.text.secondary, mb: 2 }} />
          <Typography variant="h6" color="textSecondary" gutterBottom>
            No videos found
          </Typography>
          <Typography variant="body2" color="textSecondary" align="center" mb={2}>
            Upload your first video to get started
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<CloudUploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
          >
            Upload Video
          </Button>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {sortedVideos.map((video) => (
            <Grid item xs={12} sm={6} md={4} key={video.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ position: 'relative' }}>
                  <CardMedia
                    component="div"
                    sx={{
                      height: 0,
                      paddingTop: '56.25%', // 16:9 aspect ratio
                      backgroundColor: 'rgba(0, 0, 0, 0.1)',
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      cursor: video.status === VideoStatus.READY ? 'pointer' : 'default',
                      '&:hover': {
                        '& .play-overlay': {
                          opacity: video.status === VideoStatus.READY ? 1 : 0,
                        },
                      },
                    }}
                    image={video.status === VideoStatus.READY ? `${video.url}?t=${new Date().getTime()}` : undefined}
                    onClick={() => {
                      if (video.status === VideoStatus.READY) {
                        handlePreviewClick(video);
                      }
                    }}
                  >
                    {video.status !== VideoStatus.READY && (
                      <Box
                        position="absolute"
                        top="50%"
                        left="50%"
                        sx={{ transform: 'translate(-50%, -50%)' }}
                      >
                        {video.status === VideoStatus.PROCESSING ? (
                          <CircularProgress color="inherit" />
                        ) : (
                          <VideoLibraryIcon sx={{ fontSize: 60, color: 'rgba(255, 255, 255, 0.5)' }} />
                        )}
                      </Box>
                    )}
                    
                    {video.status === VideoStatus.READY && (
                      <Box
                        className="play-overlay"
                        position="absolute"
                        top={0}
                        left={0}
                        right={0}
                        bottom={0}
                        display="flex"
                        justifyContent="center"
                        alignItems="center"
                        bgcolor="rgba(0, 0, 0, 0.5)"
                        sx={{ opacity: 0, transition: 'opacity 0.3s' }}
                      >
                        <PlayArrowIcon sx={{ fontSize: 60, color: 'white' }} />
                      </Box>
                    )}
                  </CardMedia>
                  
                  <Box
                    position="absolute"
                    top={8}
                    right={8}
                  >
                    <Chip
                      label={statusLabels[video.status]}
                      color={statusColors[video.status] as any}
                      size="small"
                    />
                  </Box>
                </Box>
                
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" gutterBottom>
                    {video.filename}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Uploaded {formatDistanceToNow(new Date(video.created_at))} ago
                  </Typography>
                  {video.size && (
                    <Typography variant="body2" color="textSecondary">
                      Size: {(video.size / (1024 * 1024)).toFixed(2)} MB
                    </Typography>
                  )}
                </CardContent>
                
                <Divider />
                
                <CardActions>
                  <Button
                    size="small"
                    color="primary"
                    startIcon={<PlayArrowIcon />}
                    disabled={video.status !== VideoStatus.READY}
                    onClick={() => handlePreviewClick(video)}
                  >
                    Watch
                  </Button>
                  
                  <Box flexGrow={1} />
                  
                  <IconButton
                    color="error"
                    size="small"
                    onClick={() => handleDeleteVideo(video.id)}
                  >
                    <DeleteIcon />
                  </IconButton>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
      
      {/* Upload Dialog */}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Upload Video</DialogTitle>
        <DialogContent>
          <VideoUpload 
            onUploadComplete={handleUploadComplete}
            onUploadError={(error) => setError(error.message)}
          />
        </DialogContent>
      </Dialog>
      
      {/* Preview Dialog */}
      <Dialog
        open={previewDialogOpen}
        onClose={() => setPreviewDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{selectedVideo?.filename}</DialogTitle>
        <DialogContent>
          {selectedVideo && (
            <Box>
              <video
                controls
                style={{ width: '100%', maxHeight: '70vh' }}
                src={selectedVideo.url}
                autoPlay
              />
              <Box mt={2}>
                <Typography variant="body2" color="textSecondary">
                  Uploaded {formatDistanceToNow(new Date(selectedVideo.created_at))} ago
                </Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Container>
  );
};

export default VideosPage; 