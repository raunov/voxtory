# Video/Audio Processing API Service

A simple and robust API service that processes video and audio files using Google Gemini API for content analysis. The service is designed to handle long-running operations efficiently through an asynchronous job system with webhook notifications.

## Architecture

This service implements a simple but effective asynchronous processing architecture:

1. **API Server**: Accepts file uploads and creates jobs
2. **Worker Thread**: Processes jobs in the background
3. **Database**: Stores job status and results (SQLite in development, PostgreSQL in production)
4. **Webhook Notifications**: Alerts clients when jobs complete

## Authentication

This service uses client-provided Gemini API keys for authentication. Each client:

1. Must provide their own Gemini API key via the `X-Gemini-API-Key` header
2. Has their jobs processed using their own API key
3. Can only access their own jobs and results

This approach eliminates the need for a separate authentication system while ensuring each client uses their own API quota.

## Requirements

- Python 3.7+
- Flask
- Requests
- python-dotenv
- google-genai
- psycopg2-binary (for PostgreSQL support)
- gunicorn (for production deployment)

## Local Development Setup

1. Clone the repository:

```bash
git clone https://github.com/your-username/n6unik_v2.git
cd n6unik_v2
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the API server (the uploads folder and database will be created automatically):

```bash
python api.py
```

4. The service will be available at http://localhost:5000

## API Endpoints

### Create a new job

```
POST /jobs
```

**Headers:**
- `X-Gemini-API-Key`: Your Gemini API key (required)

**Parameters:**
- `file`: The video or audio file to process (multipart/form-data)
- `webhook_url` (optional): URL to receive a notification when the job completes

**Response:**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Job created successfully"
}
```

### Check job status

```
GET /jobs/{job_id}
```

**Headers:**
- `X-Gemini-API-Key`: Your Gemini API key (required)

**Response (pending/processing):**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

**Response (completed):**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "results": {
    "topics": ["Topic 1", "Topic 2"],
    "summary": "Summary text...",
    "language": "detected language",
    "speakers": [...],
    "transcript": [...]
  }
}
```

**Response (failed):**
```json
{
  "job_id": "uuid",
  "status": "failed",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "error": "Error message"
}
```

### List all jobs

```
GET /jobs
```

**Headers:**
- `X-Gemini-API-Key`: Your Gemini API key (required)

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "uuid",
      "status": "completed",
      "created_at": "timestamp",
      "updated_at": "timestamp"
    },
    {
      "job_id": "uuid",
      "status": "pending",
      "created_at": "timestamp",
      "updated_at": "timestamp"
    }
  ]
}
```

## Webhook Notifications

When a job completes or fails, the service can send a POST request to a webhook URL with the job details. To use this feature, provide a `webhook_url` parameter when creating a job.

The webhook payload will be identical to the response from the `GET /jobs/{job_id}` endpoint.

## Example Usage

### Using curl

```bash
# Submit a new job with webhook
curl -X POST \
  -H "X-Gemini-API-Key: your_gemini_api_key_here" \
  -F "file=@video.mp4" \
  -F "webhook_url=https://webhook.site/your-unique-id" \
  http://localhost:5000/jobs

# Check job status
curl -H "X-Gemini-API-Key: your_gemini_api_key_here" \
  http://localhost:5000/jobs/job_id_here

# List all jobs
curl -H "X-Gemini-API-Key: your_gemini_api_key_here" \
  http://localhost:5000/jobs
```

### Using Python requests

```python
import requests

# Gemini API key for authentication
api_key = "your_gemini_api_key_here"
headers = {"X-Gemini-API-Key": api_key}

# Submit a new job
with open('video.mp4', 'rb') as f:
    files = {'file': f}
    data = {'webhook_url': 'https://webhook.site/your-unique-id'}
    response = requests.post(
        'http://localhost:5000/jobs',
        headers=headers,
        files=files,
        data=data
    )
    job_id = response.json()['job_id']

# Check job status
response = requests.get(
    f'http://localhost:5000/jobs/{job_id}',
    headers=headers
)
print(response.json())
```

## Deployment to Render

This service is ready to deploy on Render.com:

1. Push your code to GitHub
2. Create a new Web Service on Render, connected to your GitHub repo
3. Configure the following settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn api:start_api`
   - **Environment Variables**:
     - `RENDER=true` (Enables production mode)
     - Add any other config variables as needed

### Database Configuration

For production deployment, the service automatically uses PostgreSQL when deployed to Render:

1. Create a PostgreSQL database in Render
2. The service will automatically connect using the `DATABASE_URL` environment variable provided by Render

## Project Structure

```
n6unik_v2/
├── api.py              # Main Flask API server
├── worker.py           # Background worker process
├── db.py               # Database operations (SQLite/PostgreSQL)
├── config.py           # Configuration settings
├── poc.py              # Gemini API integration
├── .env                # Environment variables (local development)
├── .gitignore          # Git ignore file
├── Procfile            # Render deployment configuration
├── requirements.txt    # Python dependencies
├── uploads/            # Directory for uploaded files
└── jobs.db             # SQLite database file (dev only)
```

## Notes

- Large files (>500MB) will be rejected
- Supported file formats: mp4, avi, mov, mp3, m4a, wav, mkv
- The worker processes one job at a time to avoid overloading the system
- Webhook notifications have built-in retry logic (3 attempts with 60-second delays)
- Each user must provide their own Gemini API key
- The service never stores complete API keys, only a hash of the first 8 characters for reference
