import json, os, re, argparse
from google import genai

from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any

# load environment variables
from dotenv import load_dotenv
load_dotenv()

# Set up Gemini API client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
base_model = "gemini-2.0-pro-exp-02-05"  # Supports structured output

# Model for roles and affiliations
class RoleAffiliation(BaseModel):
    role_affiliation: str
    is_current: Optional[bool] = None  # To distinguish between current and past roles

class DetailConcept(BaseModel):
    name: str
    type: str 
    emoji: str
    description: str

class SubConcept(BaseModel):
    name: str
    type: str 
    emoji: str
    description: str
    details: Optional[List[DetailConcept]] = None  # Contains details (level 3)

class MainConcept(BaseModel):
    name: str
    type: str 
    emoji: str
    description: str
    subtopics: Optional[List[SubConcept]] = None  # Contains subtopics (level 2)

# Model for transcript entries
class TranscriptEntry(BaseModel):
    speaker: str
    timestamp: str
    text: str
    # Added visual elements as requested
    visual_description: Optional[str] = None  # For visual descriptions in the transcript

# Model for categorized statements by speakers
class Statement(BaseModel):
    text: str
    category: Literal["fact", "prediction", "insight", "anecdote", "opinion", "explanation"]

# Enhanced speaker model
class Speaker(BaseModel):
    full_name: str  # Full name or descriptor if name not available
    roles_affiliations: Optional[List[str]] = None  # List of roles and affiliations
    visual_description: Optional[str] = None  # Visual description for video or voice description for audio
    voice_description: Optional[str] = None  # Voice description if relevant
    statements: List[Statement]  # All statements made by the speaker with categories

# Main response model
class ContentAnalysis(BaseModel):
    concept_map: List[MainConcept]  # Concept map of the video content
    speakers: List[Speaker]  # Detailed information about each speaker

def get_language_prompt(language_code: str = 'en') -> str:
    """
    Get the prompt with specified language instructions
    
    Args:
        language_code (str): Language code for the output
    
    Returns:
        str: Prompt with language instructions
    """
    return f"""
You are tasked with analyzing a video recording and creating a concept map of topics discussed and dossiers for each speaker mentioned.
Additional instructions for video content:
* Include visual descriptions of scenes and actions where relevant
* Note significant visual elements alongside the audio
* Identify speakers based on both visual and audio cues
* Generate all output in the language specified by this code: {language_code}

Please follow these instructions carefully:

1. Concept Map Creation:
   Create a 3-level hierarchical concept map of the video content. For each main concept or topic discussed, include:
   - name of the concept or topic
   - level of concept topic (main concept, subtopic, detail) 
        * Main Concept: the core themes of the video
        * Subtopic: major concepts and areas within the central topics
        * Detail: specific ideas, definitions, examples and challenges related to the subtopics
   - Appropriate emoji for each topic
   - A brief description of the topic
   Present this information in a structured format. Ensure that your response maintains this exact 3-level hierarchy with no additional nested levels.

2. Speaker Identification:
   Identify speakers based on what they say about themselves or each other. Use every clue available, including:
   - Self-introductions
   - Introductions by others
   - References to past roles or affiliations
   - Visual cues (e.g., name tags, company logos)
   - Contextual clues (e.g., "the CEO of XYZ Corp", "the interviewer", etc.)
   If a speaker's name is not explicitly mentioned, use a generic descriptor that best fits their role (e.g., "Interviewer", "Guest Expert", "Company CEO").

3. Speaker Dossiers:
   For each identified speaker, create a dossier. Extract factual background information from the transcript based on what the speakers themselves or other participants say. Focus on:
   a. Full name
   b. Current and past roles and affiliations mentioned
   c. Visual descriptions of the speaker (if mentioned)
   d. Voice description (if relevant)
   e. Insightful statements uttered by the speaker, categorized as either: facts, predictions, insights, anecdotes, opinions.
   Include only the statements that are relevant to the speaker's role and expertise. Categorize each statement accordingly.

If certain information is not available, omit those fields entirely.
Ensure that your final output contains only the information requested, without any additional explanation or commentary.
Remember to focus on extracting and presenting factual information from the video/audio. Do not include any speculative or inferred information.
Generate all output in the language specified by this code: {language_code}
"""

def is_youtube_url(url: str) -> bool:
    """Check if the given string is a YouTube URL."""
    if not url:
        return False
    
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
    return bool(re.match(youtube_regex, url))

def process_video(youtube_url: str, language: str = 'en'):
    """
    Process video from a YouTube URL
    
    Args:
        youtube_url (str): YouTube URL to analyze
        language (str): Language code for the output (default: 'en' for English)
    
    Returns:
        The structured content analysis result
    """
    if not youtube_url:
        raise ValueError("YouTube URL is required")
    
    if not is_youtube_url(youtube_url):
        raise ValueError(f"Invalid YouTube URL: {youtube_url}")
    
    print(f"Processing YouTube URL: {youtube_url}")
    
    # Get the prompt with language instructions
    prompt = get_language_prompt(language)
    
    # For YouTube URL, create content using from_uri
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_uri(
                    file_uri=youtube_url,
                    mime_type="video/*",
                ),
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    
    # Count tokens for YouTube URL
    print("Counting tokens for YouTube video...")
    try:
        token_count = client.models.count_tokens(
            model=base_model, 
            contents=[
                {"role": "user", "parts": [{"text": youtube_url}, {"text": prompt}]}
            ]
        )
        print(f"Token count: {token_count}")
    except Exception as e:
        print(f"Token counting for YouTube video failed: {str(e)}")
        print("Continuing with analysis...")
        
    # Get structured content analysis directly with base model
    print("Getting structured analysis with base model for YouTube video...")
    try:
        response = client.models.generate_content(
            model=base_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", 
                response_schema=ContentAnalysis
            )
        )
        
        try:
            # Try to parse the JSON directly
            final_result = json.loads(response.text)
            print("Structured JSON received.")
            return final_result
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            print("Attempting to fix malformed JSON...")
            fixed_json = fix_json_with_gemini(response.text)
            if fixed_json:
                print("JSON successfully fixed!")
                return fixed_json
            else:
                print("Failed to fix JSON. Here's the raw response:")
                return response.text
    except Exception as e:
        print(f"Error analyzing YouTube video: {str(e)}")
        raise

def fix_json_with_gemini(response_text: str, max_attempts: int = 3) -> Optional[Dict[str, Any]]:
    """
    Attempts to fix malformed JSON using Gemini Flash model.
    
    Args:
        response_text (str): The original malformed JSON text
        max_attempts (int): Maximum number of fix attempts
        
    Returns:
        dict: Fixed and parsed JSON if successful, None otherwise
    """
    # Use the lighter Gemini model for fixing
    fix_model = "gemini-2.0-flash-lite"
    
    for attempt in range(max_attempts):
        try:
            print(f"Fix attempt {attempt+1}/{max_attempts}...")
            
            # Prompt Gemini to fix only the JSON format
            fix_prompt = f"""
            The following JSON is malformed. Fix ONLY the JSON format issues, 
            not the content. Do not add or remove any data. Return ONLY the 
            fixed JSON with no additional text or explanations:
            
            {response_text}
            """
            
            # Get fixed JSON from Gemini
            fix_response = client.models.generate_content(
                model=fix_model,
                contents=[{"role": "user", "parts": [{"text": fix_prompt}]}]
            )
            
            # Extract fixed JSON text and try to parse it
            fixed_json_text = fix_response.text
            fixed_json = json.loads(fixed_json_text)
            
            # Validate against the Pydantic model
            content_analysis = ContentAnalysis.model_validate(fixed_json)
            
            # If validation passed, return the fixed JSON
            print("JSON successfully fixed and validated with Pydantic model")
            return fixed_json
            
        except json.JSONDecodeError as e:
            print(f"JSON still malformed: {str(e)}")
        except Exception as e:
            print(f"Validation error: {str(e)}")
            
    # If we reach here, all attempts failed
    print("All fix attempts failed")
    return None

# Command line interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze YouTube videos and extract insights using Gemini API')
    parser.add_argument('--url', '-u', type=str, required=True, help='YouTube URL to analyze')
    parser.add_argument('--language', '-l', type=str, default='en', help='Output language code (e.g., "en" for English, "es" for Spanish)')
    
    args = parser.parse_args()
    
    # Process the YouTube video URL
    try:
        result = process_video(args.url, args.language)
        print(f"Final structured result (in {args.language}):")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")
