# Voxtory Video Insights API

A simple API that analyzes YouTube videos using Google's Gemini API to extract concept maps and speaker information.

## Features

- Analyze YouTube videos to extract concept maps and speaker information
- BYOK (Bring Your Own Key) authentication using Gemini API keys
- Support for multiple languages
- Easy customization of prompts
- Structured JSON response

## Installation

### Prerequisites

- Python 3.9+
- [Gemini API Key](https://ai.google.dev/)

### Local Development

1. Clone the repository
   ```bash
   git clone https://github.com/raunov/voxtory.git
   cd voxtory
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`.

### Using Docker

1. Build the Docker image
   ```bash
   docker build -t voxtory-api .
   ```

2. Run the container
   ```bash
   docker run -p 8000:8000 voxtory-api
   ```

## API Endpoints

### `GET /`

Returns basic information about the API.

### `GET /health`

Health check endpoint.

### `POST /analyze`

Analyzes a YouTube video and returns structured insights.

#### Request Body
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "language": "en"
}
```

#### Headers
- `X-Gemini-API-Key`: Your Gemini API key

#### Optional Query Parameters
- `additional_instructions`: Additional instructions to customize the analysis prompt

#### Response
```json
{
  "status": "success",
  "data": {
    "concept_map": [
      {
        "name": "Main Topic",
        "type": "main concept",
        "emoji": "🌟",
        "description": "Description of the main topic",
        "subtopics": [
          {
            "name": "Subtopic",
            "type": "subtopic",
            "emoji": "📊",
            "description": "Description of the subtopic",
            "details": [
              {
                "name": "Detail",
                "type": "detail",
                "emoji": "📝",
                "description": "Description of the detail"
              }
            ]
          }
        ]
      }
    ],
    "speakers": [
      {
        "full_name": "Speaker Name",
        "roles_affiliations": ["Role 1", "Role 2"],
        "visual_description": "Description of appearance",
        "voice_description": "Description of voice",
        "statements": [
          {
            "text": "Statement text",
            "category": "fact"
          }
        ]
      }
    ]
  }
}
```

## Usage Examples

### cURL Example

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -H "X-Gemini-API-Key: YOUR_GEMINI_API_KEY" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "language": "en"
  }'
```

### Python Example

```python
import requests
import json

url = "http://localhost:8000/analyze"
headers = {
    "Content-Type": "application/json",
    "X-Gemini-API-Key": "YOUR_GEMINI_API_KEY"
}
payload = {
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "language": "en"
}

response = requests.post(url, headers=headers, json=payload)
result = response.json()
print(json.dumps(result, indent=2))
```

## Modifying the Prompt

To customize the analysis prompt, you can modify the `app/prompts/base.py` file or use the `additional_instructions` parameter when making API requests.

## Deployment

The API is deployed on Render at `https://voxtory.onrender.com`.

## License

MIT
