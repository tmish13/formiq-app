# Video Upload Module

This module implements direct-to-S3 video uploads for FormIQ, allowing users to upload workout videos efficiently for analysis and storage. The module implements a secure, scalable approach that minimizes server load while providing a smooth user experience.

## Architecture

The video upload module uses a client-direct-to-S3 approach with the following components:

1. **Backend API Endpoints** - For generating presigned URLs and tracking uploads
2. **Frontend Components** - For handling file selection, validation, and upload UX
3. **S3 Integration** - For secure, scalable file storage

### Workflow

```
┌────────────┐     1. Request presigned URL      ┌────────────┐
│            │───────────────────────────────────▶            │
│            │                                    │            │
│            │     2. Return presigned URL        │            │
│   Client   │◀───────────────────────────────────│   Server   │
│            │                                    │            │
│            │     5. Confirm upload              │            │
│            │───────────────────────────────────▶            │
└────────────┘                                    └────────────┘
       │                                                │
       │ 3. Upload                                      │ 6. Update
       │    directly                                    │    database
       ▼                                                │
┌────────────┐                                          │
│            │                                          │
│     S3     │◀─────────────────────────────────────────┘
│            │        (optional: process video)
└────────────┘
```

1. The client requests a presigned URL from the server
2. The server generates a presigned URL with temporary access to upload to S3
3. The client uploads the file directly to S3 using the presigned URL
4. The client tracks upload progress and handles any errors
5. After a successful upload, the client confirms the upload with the server
6. The server updates the database with the video information

## Backend Components

### Models

- `Video` (SQLAlchemy model) - Stores video metadata and processing status
- `VideoStatus` (Enum) - Tracks the status of each video (PENDING, PROCESSING, READY, FAILED, DELETED)

### API Endpoints

#### 1. Get Presigned Upload URL

```
POST /videos/upload/signed-url
```

Request body:
```json
{
  "filename": "workout.mp4",
  "content_type": "video/mp4",
  "metadata": {
    "exercise_type": "squat",
    "custom_field": "value"
  }
}
```

Response:
```json
{
  "upload_url": "https://bucket-name.s3.region.amazonaws.com/...",
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "object_key": "videos/user123/timestamp_filename.mp4",
  "expires_in": 3600
}
```

#### 2. Confirm Upload

```
POST /videos/upload/confirm
```

Request body:
```json
{
  "video_id": "123e4567-e89b-12d3-a456-426614174000",
  "object_key": "videos/user123/timestamp_filename.mp4",
  "size": 15728640
}
```

Response: Video object with updated status

#### 3. Get Video

```
GET /videos/{video_id}
```

Response: Full video object with metadata

#### 4. List Videos

```
GET /videos?skip=0&limit=20&status=ready
```

Response: Array of video objects

#### 5. Delete Video

```
DELETE /videos/{video_id}
```

Response: 204 No Content

### Storage Service

The `StorageService` class handles interaction with the storage provider (S3), including:
- Generating presigned URLs for uploads
- Getting public URLs for access
- Deleting files from storage

## Frontend Components

### Components

#### 1. VideoUpload Component

A reusable React component (`VideoUpload.tsx`) that handles:
- File selection via drag-and-drop or file picker
- File validation (size, type, duration)
- Progress tracking with cancel option
- Error handling
- Upload confirmation

#### 2. Videos Page

A page component (`Videos.tsx`) that provides:
- List of user's videos with status indicators
- Video preview and playback
- Sort and filter options
- Delete functionality
- Upload dialog

### Services

#### Video Service

A TypeScript service (`videos.ts`) that provides:
- API client for video endpoints
- TypeScript interfaces for video data
- Upload helpers with progress tracking

## Client Usage

### Basic Usage

```tsx
import { VideoUpload } from '../components/VideoUpload';
import { Video } from '../services/videos';

const MyComponent = () => {
  const handleUploadComplete = (video: Video) => {
    console.log('Upload complete:', video);
    // Do something with the video
  };

  return (
    <div>
      <h1>Upload Workout Video</h1>
      <VideoUpload onUploadComplete={handleUploadComplete} />
    </div>
  );
};
```

### Advanced Usage

```tsx
import { useState } from 'react';
import { videoService, Video, VideoStatus } from '../services/videos';

const AdvancedUpload = () => {
  const [videos, setVideos] = useState<Video[]>([]);
  
  const uploadVideo = async (file: File) => {
    try {
      const video = await videoService.uploadVideo(
        file, 
        (progress) => console.log(`Upload progress: ${progress}%`)
      );
      setVideos(prev => [video, ...prev]);
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };
  
  return (
    <div>
      {/* Custom implementation here */}
    </div>
  );
};
```

## Security Considerations

1. **Presigned URLs** - URLs are temporary and expire after a set time (default: 1 hour)
2. **Content Type Verification** - Only allowed video types can be uploaded
3. **User Ownership** - Videos are associated with user accounts and access is restricted
4. **Server-Side Validation** - File metadata is validated on the server
5. **Rate Limiting** - Endpoints are rate-limited to prevent abuse

## Configuration

### Backend Environment Variables

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
AWS_BUCKET_NAME=your-bucket-name
MAX_VIDEO_SIZE_MB=100
MAX_VIDEO_DURATION_SECONDS=300
```

### Frontend Configuration

File size and duration limits are defined in the `VideoUpload` component:

```typescript
// Maximum file size in bytes (100MB)
const MAX_FILE_SIZE = 100 * 1024 * 1024;
// Maximum video duration in seconds (5 minutes)
const MAX_DURATION = 5 * 60;
// Allowed video types
const ALLOWED_TYPES = ['video/mp4', 'video/webm', 'video/quicktime'];
```

## Future Enhancements

1. **Video Processing** - Implement server-side processing for video conversion and optimization
2. **Video Thumbnails** - Generate and store thumbnails for better UX
3. **Multi-Part Uploads** - Support for large files using S3 multi-part uploads
4. **Video Categories** - Add tagging and categorization
5. **Public/Private Sharing** - Allow users to share videos publicly or with specific users 