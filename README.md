# Voxtory

A RESTful API that leverages Google Gemini's AI capabilities to analyze spoken content in audio recordings, providing context and insights for events and meetings.

## Features

- **Audio Processing**: Upload audio files for transcription and analysis.
- **Speaker Identification**: Distinguishes between different speakers (when possible).
- **Content Analysis**: Extracts key topics, statements, and facts.
- **Insight Generation**: Provides summaries and key takeaways.
- **Token Authentication**: Secure API access with token-based authentication.
- **Rate Limiting**: Protects against API abuse.

## API Overview

The application exposes the following endpoints:

- `GET /api/status`: Check API status and validate authentication
- `POST /api/analyze`: Analyze audio file (requires authentication)
- `GET /`: Test interface for API interaction

## Setup Instructions

### Prerequisites

- Python 3.8+
- Gemini API key from Google AI Studio (https://aistudio.google.com/app/apikey)

### Installation

1. Configure the Gemini API key:
   - Edit the `.env` file in the backend directory
   - Replace the existing API key with your actual Gemini API key

2. (Optional) Configure API tokens:
   - By default, a random API token is generated when the server starts
   - To set specific API tokens, add an `API_TOKEN` value to the `.env` file
   - Multiple tokens can be specified as comma-separated values

3. Install dependencies:
   ```
   cd backend
   install_deps.bat
   ```

## Running the Application

1. Start the server:
   ```
   cd backend
   run_server.bat
   ```

2. The server will start at http://localhost:8000

## Using the API

### Authentication

All API requests require a valid API token provided in the `X-API-Key` header:

```
X-API-Key: your_api_token
```

### Testing the API

1. Use the built-in test interface at http://localhost:8000
2. Run the test script to verify API functionality:
   ```
   cd backend
   python test_server.py
   ```

### API Endpoints

#### GET /api/status

Check the API status and validate your authentication token.

**Request:**
```
GET /api/status
X-API-Key: your_api_token
```

**Response:**
```json
{
  "status": "ok", 
  "message": "API is running and authentication is valid",
  "timestamp": "2025-03-02 23:35:00"
}
```

#### GET /api/health

Check the API health status (for monitoring and load balancers). No authentication required.

**Request:**
```
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-03-02 23:35:00"
}
```

#### POST /api/analyze (Synchronous)

Analyze an audio file synchronously. Note: This endpoint may time out for large files or complex analyses.

**Request:**
```
POST /api/analyze
X-API-Key: your_api_token
Content-Type: multipart/form-data

[audiofile binary data]
```

**Response:**
```json
{
  "result": "JSON analysis results as structured data"
}
```

#### POST /api/jobs (Asynchronous)

Start an asynchronous audio analysis job. This endpoint is recommended for larger files or when you want to avoid request timeouts.

**Request:**
```
POST /api/jobs
X-API-Key: your_api_token
Content-Type: multipart/form-data

[audiofile binary data]
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job created successfully",
  "check_url": "/api/jobs/550e8400-e29b-41d4-a716-446655440000"
}
```

#### GET /api/jobs/{job_id}

Check the status of an asynchronous job and retrieve results when complete.

**Request:**
```
GET /api/jobs/550e8400-e29b-41d4-a716-446655440000
X-API-Key: your_api_token
```

**Response (while processing):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": 1709505600,
  "updated_at": 1709505605,
  "filename": "example.mp3",
  "file_size": 1048576
}
```

**Response (when complete):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": 1709505600,
  "updated_at": 1709505650,
  "filename": "example.mp3",
  "file_size": 1048576,
  "result": "JSON analysis results as structured data"
}
```

**Response (if failed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "created_at": 1709505600,
  "updated_at": 1709505610,
  "filename": "example.mp3",
  "file_size": 1048576,
  "error": "Error message describing what went wrong"
}
```

## Rate Limiting

The API includes rate limiting to prevent abuse:
- Default: 10 requests per minute per API token
- Configurable via the `RATE_LIMIT` environment variable

## Security Notes

- The API uses token-based authentication
- CORS settings automatically restrict to specific origins in production mode
- API keys for Gemini requests are sent in secure headers instead of URLs
- Temporary files are properly cleaned up even in error conditions
- The application runs as a non-root user in Docker containers

## Error Handling

The API provides clear error messages with appropriate HTTP status codes:
- 401: Unauthorized (invalid API token)
- 413: Payload too large (file size exceeds limit)
- 415: Unsupported media type (not an audio file)
- 429: Too many requests (rate limit exceeded)
- 500: Internal server error

## Deployment to Render

This application is configured for easy deployment to Render using Docker.

### Prerequisites for Deployment

1. A Render account (https://render.com)
2. Git repository with your code
3. Gemini API key from Google AI Studio

### Deployment Options

#### Option 1: Manual Deployment

1. Log in to your Render dashboard
2. Create a new Web Service
3. Connect your repository
4. Choose "Docker" as the Environment
5. Set the following environment variables:
   - `ENVIRONMENT`: `production`
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `API_TOKEN`: Your chosen API token(s)
   - `CORS_ORIGINS`: Comma-separated list of allowed origins (e.g., `https://yourdomain.com,https://app.yourdomain.com`)
   - `RATE_LIMIT`: Request rate limit (e.g., 10)
   - `LOG_LEVEL`: `INFO`
6. Click "Create Web Service"

#### Option 2: Using Render Blueprint (Recommended)

1. Ensure your repository includes the `render.yaml` file provided in this project
2. In the Render dashboard, click "Blueprint" and select your repository
3. Render will automatically set up the service as defined in the blueprint
4. You'll need to manually set these environment variables in the Render dashboard:
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `CORS_ORIGINS`: Comma-separated list of allowed origins (e.g., `https://yourdomain.com,https://app.yourdomain.com`)

   These values are marked with `sync: false` for security reasons and must be set manually.

### Post-Deployment Setup

1. The first deploy may take a few minutes as the Docker image is built
2. Once deployed, your API will be available at the URL provided by Render
3. Note your API token(s) for clients to use when accessing the API
4. Update your frontend applications to use the new API endpoint

### Monitoring

- Use the `/api/health` endpoint for health checks
- Set up Render alerts for monitoring service health
- Check logs in the Render dashboard for troubleshooting

### Important Deployment Notes

- **Job Storage**: The current implementation stores jobs in memory, which means:
  - Jobs are lost when the server restarts
  - Not suitable for multi-instance deployments without modifications
  - Consider implementing database persistence for production use

- **Rate Limiting**: The current implementation uses in-memory storage, which:
  - Works fine for single-instance deployments
  - Not suitable for multi-instance deployments without a shared cache (like Redis)
