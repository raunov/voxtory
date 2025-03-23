import json, re, os
from google import genai
from google.genai import types
import logging
from app.prompts.base import get_language_prompt
from app.models import ContentAnalysis
from typing import Optional, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gemini model to use
base_model = "gemini-2.0-pro-exp-02-05"  # Supports structured output

def is_youtube_url(url: str) -> bool:
    """Check if the given string is a YouTube URL."""
    if not url:
        return False
    
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
    return bool(re.match(youtube_regex, url))

def setup_gemini_client(api_key: str):
    """Set up and return a Gemini API client with the provided API key"""
    if not api_key:
        raise ValueError("Gemini API Key is required")
    
    return genai.Client(api_key=api_key)

def process_video(youtube_url: str, language: str = 'en', api_key: str = None, additional_instructions: str = ''):
    """
    Process video from a YouTube URL
    
    Args:
        youtube_url (str): YouTube URL to analyze
        language (str): Language code for the output (default: 'en' for English)
        api_key (str): Gemini API key
        additional_instructions (str): Any additional instructions to append to the prompt
    
    Returns:
        The structured content analysis result
    """
    if not youtube_url:
        raise ValueError("YouTube URL is required")
    
    if not is_youtube_url(youtube_url):
        raise ValueError(f"Invalid YouTube URL: {youtube_url}")
    
    logger.info(f"Processing YouTube URL: {youtube_url}")
    
    # Set up Gemini client
    client = setup_gemini_client(api_key)
    
    # Get the prompt with language instructions
    prompt = get_language_prompt(language, additional_instructions)
    
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
    logger.info("Counting tokens for YouTube video...")
    try:
        token_count = client.models.count_tokens(
            model=base_model, 
            contents=[
                {"role": "user", "parts": [{"text": youtube_url}, {"text": prompt}]}
            ]
        )
        logger.info(f"Token count: {token_count}")
    except Exception as e:
        logger.warning(f"Token counting for YouTube video failed: {str(e)}")
        logger.info("Continuing with analysis...")
        
    # Get structured content analysis directly with base model
    logger.info("Getting structured analysis with base model for YouTube video...")
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
            logger.info("Structured JSON received.")
            return final_result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {str(e)}")
            logger.info("Attempting to fix malformed JSON...")
            fixed_json = fix_json_with_gemini(client, response.text)
            if fixed_json:
                logger.info("JSON successfully fixed!")
                return fixed_json
            else:
                logger.warning("Failed to fix JSON. Returning raw response.")
                return {"raw_response": response.text}
    except Exception as e:
        logger.error(f"Error analyzing YouTube video: {str(e)}")
        raise

def fix_json_with_gemini(client, response_text: str, max_attempts: int = 3) -> Optional[Dict[str, Any]]:
    """
    Attempts to fix malformed JSON using Gemini Flash model.
    
    Args:
        client: Gemini API client
        response_text (str): The original malformed JSON text
        max_attempts (int): Maximum number of fix attempts
        
    Returns:
        dict: Fixed and parsed JSON if successful, None otherwise
    """
    # Use the lighter Gemini model for fixing
    fix_model = "gemini-2.0-flash-lite"
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"Fix attempt {attempt+1}/{max_attempts}...")
            
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
            logger.info("JSON successfully fixed and validated with Pydantic model")
            return fixed_json
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON still malformed: {str(e)}")
        except Exception as e:
            logger.warning(f"Validation error: {str(e)}")
            
    # If we reach here, all attempts failed
    logger.warning("All fix attempts failed")
    return None
