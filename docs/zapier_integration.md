# FormIQ Zapier Integration Guide

This guide demonstrates how to set up Zapier integrations to automatically collect training data for improving FormIQ's exercise form analysis models.

## Overview

Zapier allows you to connect FormIQ with various data sources to automatically collect high-quality training data for your ML models. The backend includes dedicated API endpoints that Zapier can use to submit this data.

## API Endpoints for Zapier

The FormIQ backend provides these endpoints for Zapier integration:

1. **Submit Exercise Data**: `POST /api/v1/training/submit`
2. **Submit Video with Metadata**: `POST /api/v1/training/submit_video`

## Authentication

All API requests require an API key:

```
Authorization: Bearer YOUR_API_KEY
```

Get an API key from your FormIQ admin dashboard.

## Data Collection Sources

### 1. YouTube Exercise Videos

Set up a Zap to monitor fitness channels and send high-quality exercise videos to FormIQ:

#### Trigger: New Video in YouTube Channel/Playlist
- Choose specific channels known for good form (AthleanX, JeffNippard, etc.)
- Filter by exercise keywords ('squat form', 'deadlift technique')

#### Action: FormIQ Training Data API
- Send to: `POST /api/v1/training/submit`
- Data format:
```json
{
  "exercise_type": "squat", 
  "source": "youtube",
  "expert_score": 0.95,
  "feedback": ["Good depth", "Proper knee tracking"],
  "metadata": {
    "video_id": "abc123",
    "channel_name": "ExpertTrainer",
    "title": "Perfect Squat Form Tutorial"
  },
  "video_url": "https://www.youtube.com/watch?v=abc123"
}
```

### 2. Google Forms for Trainer Feedback

Create a Google Form for exercise trainers to evaluate form and automatically send results:

#### Trigger: New Form Submission
- Design a form with fields for exercise type, score, and feedback

#### Action: FormIQ Training Data API
- Map form fields to API fields
- Example mapping:
  - "Exercise Type" → exercise_type
  - "Form Score (0-100)" → expert_score (divide by 100)
  - "Form Feedback" → feedback (split by line breaks)

### 3. Fitness Apps via Webhooks

Connect with fitness apps that provide exercise form data:

#### Trigger: Webhook from Partner Fitness App
- Set up in supported apps like TrainHeroic, FitBot

#### Action: Send data to FormIQ API
- Transform webhook data to match FormIQ's API format

### 4. Dropbox/Google Drive for Exercise Videos

Monitor cloud storage folders for new exercise videos:

#### Trigger: New File in Folder
- Set folder path: "/Exercise Videos/Training Data"
- Filter by file extensions: mp4, mov, avi

#### Action: FormIQ Video API
- Download file and submit to `POST /api/v1/training/submit_video`
- Include metadata in separate field

## Sample Zaps

### YouTube to FormIQ

1. **Trigger**: New video in YouTube playlist
2. **Filter**: Video title contains exercise keyword
3. **Action**: FormIQ API - Submit training data with video URL

### Google Form to FormIQ

1. **Trigger**: New submission in Google Form
2. **Transform**: Format data to match API requirements
3. **Action**: FormIQ API - Submit trainer evaluation

### Airtable to FormIQ

1. **Trigger**: New record in Airtable "Exercise Database"
2. **Filter**: Only records with "Include in Training" checked
3. **Action**: FormIQ API - Submit structured training data

## Best Practices

1. **Data Quality Control**:
   - Use filters to ensure only high-quality data is sent
   - Set minimum thresholds for video quality, ratings

2. **Metadata Enrichment**:
   - Add source details, expert credentials, context
   - Tag data appropriately for filtering during training

3. **Rate Limiting**:
   - Configure reasonable polling intervals
   - Respect API rate limits

4. **Error Handling**:
   - Set up error notifications in Zapier
   - Monitor failed submissions

## Testing Your Zaps

1. Test each Zap with sample data before activating
2. Verify data appears correctly in FormIQ admin dashboard
3. Monitor model improvement metrics after new data collection

## Example JSON Payload

```json
{
  "exercise_type": "deadlift",
  "source": "fitness_app_partner",
  "expert_score": 0.85,
  "feedback": [
    "Hips rising too quickly",
    "Good back position",
    "Needs more tension in lats"
  ],
  "metadata": {
    "trainer_id": "T12345",
    "certification": "NSCA-CSCS",
    "years_experience": 8,
    "recording_equipment": "iPhone 13 Pro"
  },
  "video_url": "https://storage.example.com/videos/deadlift_analysis_123.mp4",
  "user_height_cm": 178,
  "user_weight_kg": 82
}
```

## Zapier API Key Security

- Never expose your API key in public Zaps
- Use Zapier's built-in encryption for sensitive data
- Rotate API keys periodically

## Support

For assistance setting up Zapier integrations:
- Email: support@formiq.com
- Documentation: https://docs.formiq.com/zapier 