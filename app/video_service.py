import json, re, os
import zlib
import base64
from google import genai
from google.genai import types
import logging
from app.prompts.base import get_language_prompt
from app.models import ContentAnalysis
from typing import Optional, Dict, Any, List

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
            
            # Generate mermaid chart from concept map if it exists
            if 'concept_map' in final_result and final_result['concept_map']:
                logger.info("Generating mermaid chart visualization...")
                
                # Generate mermaid code
                mermaid_code = generate_mermaid_from_concept_map(client, final_result['concept_map'], language)
                
                # Encode mermaid code for URL
                mermaid_url = encode_mermaid_for_url(mermaid_code)
                
                # Add mermaid URL to the result
                final_result['mermaid_chart_url'] = mermaid_url
                logger.info(f"Added mermaid chart URL: {mermaid_url}")
            
            return final_result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {str(e)}")
            logger.info("Attempting to fix malformed JSON...")
            fixed_json = fix_json_with_gemini(client, response.text)
            if fixed_json:
                logger.info("JSON successfully fixed!")
                
                # Generate mermaid chart from fixed JSON concept map if it exists
                if 'concept_map' in fixed_json and fixed_json['concept_map']:
                    logger.info("Generating mermaid chart visualization from fixed JSON...")
                    
                    # Generate mermaid code
                    mermaid_code = generate_mermaid_from_concept_map(client, fixed_json['concept_map'], language)
                    
                    # Encode mermaid code for URL
                    mermaid_url = encode_mermaid_for_url(mermaid_code)
                    
                    # Add mermaid URL to the result
                    fixed_json['mermaid_chart_url'] = mermaid_url
                    logger.info(f"Added mermaid chart URL: {mermaid_url}")
                
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

def generate_mermaid_from_concept_map(client, concept_map: List[Dict[str, Any]], language: str = 'en') -> str:
    """
    Generate mermaid mindmap code from concept map JSON using Gemini.
    
    Args:
        client: Gemini API client
        concept_map: List of concept map entries
        language: Language code for output
        
    Returns:
        str: Generated mermaid code
    """
    # Use the flash-lite model for mermaid generation
    mermaid_model = "gemini-2.0-flash-lite"
    
    logger.info("Generating mermaid chart from concept map...")
    
    # Create a prompt with example mermaid format
    prompt = f"""
    Create a 3 level mermaid mind map from the following concept map data:
    
    {json.dumps(concept_map, indent=2)}
    
    Follow this exact format for the mindmap:
    mindmap
        root(("**⚙️ Root concept**<br>Description"))
            main_concept1("**💡 Main concept**<br>Description")
                sub_concept1("**🔍 Sub concept**<br>Description")
            main_concept2(...)
    
    Use the emoji from each concept in the diagram. Format each node with bold title and description on new line with <br> tag.
    The root node should use double parentheses (( )), and all other nodes should use regular parentheses ( ).
    Return ONLY the mermaid code with no additional text or explanations.
    """
    
    try:
        # Generate mermaid code with Gemini
        response = client.models.generate_content(
            model=mermaid_model,
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        # Extract generated mermaid code
        mermaid_code = response.text.strip()
        
        # Make sure it starts with 'mindmap'
        if not mermaid_code.startswith("mindmap"):
            mermaid_code = "mindmap\n" + mermaid_code
            
        logger.info("Successfully generated mermaid chart")
        return mermaid_code
        
    except Exception as e:
        logger.error(f"Error generating mermaid chart: {str(e)}")
        # Return a simple fallback mermaid chart on error
        return "mindmap\n    root((\"Unable to generate chart\"))"

def encode_mermaid_for_url(mermaid_code: str) -> str:
    """
    Encode mermaid code to be used in a mermaid.ink URL
    
    Args:
        mermaid_code: Mermaid chart code
        
    Returns:
        str: URL to the mermaid chart visualization
    """
    logger.info("Encoding mermaid chart for URL...")
    try:
        # Compress with zlib (pako compatible)
        compressed = zlib.compress(mermaid_code.encode('utf-8'))
        
        # Convert to base64 and make URL-safe
        encoded = base64.urlsafe_b64encode(compressed).decode('ascii')
        
        # Create the mermaid.ink URL
        mermaid_url = f"https://mermaid.ink/img/pako:{encoded}"
        
        logger.info("Successfully encoded mermaid chart URL")
        return mermaid_url
        
    except Exception as e:
        logger.error(f"Error encoding mermaid chart: {str(e)}")
        return "https://mermaid.ink/img/error"
