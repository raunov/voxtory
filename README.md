# Voxtory

A RESTful API that leverages Google Gemini's AI capabilities to analyze spoken content in audio recordings, providing context and insights for events and meetings. The service is designed to handle long-running operations efficiently through an asynchronous job system with webhook notifications.

## Architecture

This service implements a simple but effective asynchronous processing architecture:

1. **API Server**: Accepts file uploads and creates jobs
2. **Worker Thread**: Processes jobs in the background
3. **Database**: Stores job status and results (SQLite for both development and production)
4. **Webhook Notifications**: Alerts clients when jobs complete

## Authentication

This service uses client-provided Gemini API keys for authentication. Each client:

1. Must provide their own Gemini API key via the `X-Gemini-API-Key` header
2. Has their jobs processed using their own API key
3. Can only access their own jobs and results

This approach eliminates the need for a separate authentication system while ensuring each client uses their own API quota.

## Requirements

- Python 3.9+
- Flask
- Requests
- python-dotenv
- google-genai
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
- `file`: The video or audio file to process (multipart/form-data) OR
- `url`: A YouTube URL or direct link to a media file
- `webhook_url` (optional): URL to receive a notification when the job completes

**Note**: You must provide either a file upload OR a URL, not both.

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
# Submit a new job with file upload
curl -X POST \
  -H "X-Gemini-API-Key: your_gemini_api_key_here" \
  -F "file=@video.mp4" \
  -F "webhook_url=https://webhook.site/your-unique-id" \
  http://localhost:5000/jobs

# Submit a new job with YouTube URL
curl -X POST \
  -H "X-Gemini-API-Key: your_gemini_api_key_here" \
  -F "url=https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  -F "webhook_url=https://webhook.site/your-unique-id" \
  http://localhost:5000/jobs

# Submit a new job with direct media URL
curl -X POST \
  -H "X-Gemini-API-Key: your_gemini_api_key_here" \
  -F "url=https://example.com/sample-video.mp4" \
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

# Submit a new job with file upload
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

# OR submit a new job with URL
data = {
    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'webhook_url': 'https://webhook.site/your-unique-id'
}
response = requests.post(
    'http://localhost:5000/jobs',
    headers=headers,
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

For simplicity and reliability, this service uses SQLite for both development and production environments. SQLite provides several advantages:

1. **Zero Configuration**: No separate database service to set up
2. **Automatic Reset**: On each deployment, the database starts fresh
3. **Ideal for Stateless Apps**: Perfect for beta testing where persistence between deployments isn't critical

The database file is stored in the application's filesystem, which is temporary but persistent during the lifetime of a deployment.

## Project Structure

```
n6unik_v2/
├── api.py                    # Main Flask API server
├── worker.py                 # Background worker process
├── db.py                     # Database operations (SQLite)
├── config.py                 # Configuration settings
├── poc.py                    # Gemini API integration
├── url_downloader.py         # URL validation and downloading utilities
├── test_url_functionality.py # Test script for URL functionality
├── .env                      # Environment variables (local development)
├── .gitignore                # Git ignore file
├── Procfile                  # Render deployment configuration
├── requirements.txt          # Python dependencies
├── uploads/                  # Directory for uploaded files
└── jobs.db                   # SQLite database file
```

## Notes

- Large files (>500MB) will be rejected
- Supported file formats: mp4, avi, mov, mp3, m4a, wav, mkv
- The worker processes one job at a time to avoid overloading the system
- Webhook notifications have built-in retry logic (3 attempts with 60-second delays)
- Each user must provide their own Gemini API key
- The service never stores complete API keys, only a hash of the first 8 characters for reference
