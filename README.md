# Voxtory Video Insights API

A simple API that analyzes YouTube videos using Google's Gemini API to extract concept maps and speaker information.

## Features

- Analyze YouTube videos to extract concept maps and speaker information
- BYOK (Bring Your Own Key) authentication using Gemini API keys
- Support for multiple languages
- Easy customization of prompts
- Structured JSON response
- Markdown output format option for human-readable results

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

Analyzes a YouTube video or a publicly accessible Google Drive file and returns structured insights.

Provide **either** `youtube_url` **or** `google_drive_id`.

#### Request Body
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID", // OR google_drive_id
  "google_drive_id": "YOUR_GOOGLE_DRIVE_FILE_ID", // OR youtube_url
  "language": "en",
  "format": "json"
}
```

**Note on Google Drive Files:**
- The file associated with `google_drive_id` **must be publicly accessible** (e.g., "Anyone with the link can view").
- The API attempts to download the file directly. Due to Google's security measures, downloads might fail for files larger than 100MB which trigger a virus scan warning page. For guaranteed processing of large files, consider alternative upload methods if needed.

The `format` parameter accepts the following values:
- `"json"` (default): Returns the data in JSON format
- `"markdown"`: Returns the data in Markdown format
- `"both"`: Returns both JSON data and a Markdown representation

#### Headers
- `X-Gemini-API-Key`: Your Gemini API key

#### Optional Query Parameters
- `additional_instructions`: Additional instructions to customize the analysis prompt

#### Response (JSON format)
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
    ],
    "mermaid": {
      "mermaid_code": "mindmap\n    root((\"Main Topic\"))\n        Subtopic1(\"Subtopic 1\")\n        Subtopic2(\"Subtopic 2\")",
      "mermaid_url": "https://mermaid.ink/img/..."
    }
  }
}
```

#### Response (Markdown format)
When requesting `format: "markdown"`, the response will be:

```json
{
  "status": "success",
  "data": {
    "markdown": "# 📊 Video Analysis\n\n## 📊 Concept Map\n\n![Concept Map](https://mermaid.ink/img/...)\n\n## 💡 Key Concepts\n\n### 🌟 Main Topic\n*Description of the main topic*\n\n..."
  }
}
```

## Usage Examples

### cURL Example

**Using YouTube URL:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -H "X-Gemini-API-Key: YOUR_GEMINI_API_KEY" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "language": "en",
    "format": "json"
  }'
```

**Using Google Drive ID:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -H "X-Gemini-API-Key: YOUR_GEMINI_API_KEY" \
  -d '{
    "google_drive_id": "YOUR_GOOGLE_DRIVE_FILE_ID",
    "language": "en",
    "format": "markdown" 
  }'
```

### Python Example

```python
import requests
import json

API_URL = "http://localhost:8000/analyze"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" # Replace with your key

headers = {
    "Content-Type": "application/json",
    "X-Gemini-API-Key": GEMINI_API_KEY
}

# Example using YouTube URL
payload_youtube = {
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "language": "en",
    "format": "json"  # Options: "json", "markdown", or "both"
}

# Example using Google Drive ID
payload_gdrive = {
    "google_drive_id": "YOUR_GOOGLE_DRIVE_FILE_ID",
    "language": "en",
    "format": "both" 
}

# Choose which payload to send
payload_to_send = payload_gdrive # Or payload_youtube

try:
    response = requests.post(API_URL, headers=headers, json=payload_to_send)
    response.raise_for_status() # Raise an exception for bad status codes
    result = response.json()
    print(json.dumps(result, indent=2))
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
    if response:
        print(f"Response status: {response.status_code}")
        try:
            print(f"Response body: {response.json()}")
        except json.JSONDecodeError:
            print(f"Response body (non-JSON): {response.text}")

```

## Modifying the Prompt

To customize the analysis prompt, you can modify the `app/prompts/base.py` file or use the `additional_instructions` parameter when making API requests.

## Markdown Output Format

When requesting data in Markdown format, the response follows this structure:

```markdown
# 📊 Video Title

## 📊 Concept Map
![Concept Map](link-to-mermaid-diagram)

## 💡 Key Concepts
### 🌟 Main Topic
*Description of the main topic*

#### 📊 Subtopic
*Description of the subtopic*

- **📝 Detail**: Description of the detail

## 👥 Speakers
### Speaker Name
**Roles/Affiliations**: Role 1, Role 2
**Visual Description**: Description of appearance
**Voice Description**: Description of voice

#### Key Statements:
**📝 Fact**
- "Statement text"

**💡 Insight**
- "Statement text"
```

This format is designed to be human-readable and can be easily viewed in any Markdown renderer.

## Deployment

The API is deployed on Render at `https://voxtory.onrender.com`.

## License

MIT
