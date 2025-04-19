import json, re, os, requests, tempfile, shutil, mimetypes, time
from google import genai
from google.genai import types, errors as google_genai_errors # Import errors
from google.api_core import exceptions as google_exceptions
import logging
from app.prompts.base import get_language_prompt
from app.models import ContentAnalysis
from typing import Optional, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gemini models
base_model = "gemini-2.5-pro-preview-03-25" 
fix_model = "gemini-2.0-flash" # Use Flash for fixing JSON

# --- Helper Functions ---

def _is_youtube_url(url: str) -> bool:
    """Check if the given string is a valid YouTube URL."""
    if not url:
        return False
    
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
    return bool(re.match(youtube_regex, url))

def setup_gemini_client(api_key: str):
    """Set up and return a Gemini API client with the provided API key"""
    if not api_key:
        raise ValueError("Gemini API Key is required")
    
    return genai.Client(api_key=api_key)

def _download_google_drive_file(file_id: str) -> str:
    """
    Downloads a publicly accessible Google Drive file to a temporary location.
    
    Args:
        file_id (str): The Google Drive file ID.
        
    Returns:
        tuple[str, Optional[str]]: A tuple containing the path to the temporary 
                                   downloaded file and the original filename 
                                   (if found in headers, otherwise None).
        
    Raises:
        ValueError: If the download fails (e.g., invalid ID, not public, network error).
    """
    logger.info(f"Attempting to download Google Drive file ID: {file_id}")
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    temp_dir = tempfile.mkdtemp()
    # Use a generic name first, try to get real name later if possible
    temp_file_path = os.path.join(temp_dir, f"gdrive_{file_id}") 
    original_filename = None # Initialize filename

    try:
        with requests.get(download_url, stream=True, timeout=60) as r:
            r.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            
            # Try to get filename from headers if available
            content_disposition = r.headers.get('content-disposition')
            if content_disposition:
                filenames = re.findall('filename="(.+)"', content_disposition)
                if filenames:
                    original_filename = filenames[0]
                    # Update temp_file_path with actual filename if found
                    new_temp_file_path = os.path.join(temp_dir, original_filename)
                    if os.path.exists(temp_file_path): # Should not exist yet, but check
                         os.remove(temp_file_path)
                    temp_file_path = new_temp_file_path
                    logger.info(f"Found original filename: {original_filename}")

            logger.info(f"Downloading to temporary file: {temp_file_path}")
            with open(temp_file_path, 'wb') as f:
                # Download in chunks for potentially large files
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
            
            logger.info(f"Successfully downloaded Google Drive file to {temp_file_path}")
            return temp_file_path, original_filename # Return path and filename
            
    except requests.exceptions.HTTPError as e:
        # Re-raise HTTPError to be caught specifically by the caller
        shutil.rmtree(temp_dir) # Clean up temp dir
        logger.error(f"HTTP error downloading Google Drive file {file_id}: {e}")
        raise e 
    except requests.exceptions.RequestException as e:
        # Handle other network errors (Connection, Timeout, etc.)
        shutil.rmtree(temp_dir) # Clean up temp dir
        logger.error(f"Network error downloading Google Drive file {file_id}: {e}")
        # Raise the original exception for the caller to handle network issues
        raise e
    except Exception as e:
        # Catch any other unexpected errors during download/saving
        shutil.rmtree(temp_dir) # Clean up temp dir
    logger.error(f"Unexpected error during Google Drive file download {file_id}: {e}", exc_info=True)
    # Raise a generic ValueError for unexpected issues
    raise ValueError(f"An unexpected error occurred while downloading Google Drive file {file_id}.")


def _clean_and_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to clean and parse a JSON string using deterministic methods.

    Args:
        text (str): The potentially malformed JSON string.

    Returns:
        Optional[Dict[str, Any]]: Parsed JSON dictionary if successful, None otherwise.
    """
    logger.debug("Attempting direct JSON parse...")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.debug("Direct parse failed. Trying cleaning...")

    # 1. Strip whitespace and common markdown fences
    cleaned_text = text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith("```"):
         cleaned_text = cleaned_text[3:] # Handle generic code fence start

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
    cleaned_text = cleaned_text.strip() # Strip again after removing fences

    logger.debug("Attempting parse after stripping fences...")
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        logger.debug("Parse after stripping fences failed. Trying substring extraction...")

    # 2. Extract content between first {/[ and last }/]
    start_brace = cleaned_text.find('{')
    start_bracket = cleaned_text.find('[')
    end_brace = cleaned_text.rfind('}')
    end_bracket = cleaned_text.rfind(']')

    start = -1
    end = -1

    # Determine the start index (first '{' or '[')
    if start_brace != -1 and start_bracket != -1:
        start = min(start_brace, start_bracket)
    elif start_brace != -1:
        start = start_brace
    elif start_bracket != -1:
        start = start_bracket

    # Determine the end index (last '}' or ']')
    if end_brace != -1 and end_bracket != -1:
        end = max(end_brace, end_bracket)
    elif end_brace != -1:
        end = end_brace
    elif end_bracket != -1:
        end = end_bracket

    if start != -1 and end != -1 and start < end:
        extracted_text = cleaned_text[start:end+1]
        logger.debug("Attempting parse after substring extraction...")
        try:
            return json.loads(extracted_text)
        except json.JSONDecodeError as e_extract:
            logger.warning(f"Substring extraction parse failed: {e_extract}")
            return None # Failed all deterministic attempts
    else:
        logger.warning("Could not find valid start/end markers for JSON extraction.")
        return None # Failed all deterministic attempts


# --- Main Processing Function ---

def process_video(source_value: str, source_type: str, language: str = 'en', api_key: str = None, additional_instructions: str = ''):
    """
    Process video/file from a YouTube URL or Google Drive ID.
    
    Args:
        source_value (str): YouTube URL or Google Drive File ID.
        source_type (str): Either 'youtube' or 'google_drive'.
        language (str): Language code for the output (default: 'en' for English).
        api_key (str): Gemini API key.
        additional_instructions (str): Any additional instructions to append to the prompt.
    
    Returns:
        The structured content analysis result.
    """
    if not source_value:
        raise ValueError("Source value (URL or ID) is required")
        
    logger.info(f"Processing {source_type}: {source_value}")
    
    # Set up Gemini client
    client = setup_gemini_client(api_key)
    
    # Get the prompt with language instructions
    prompt = get_language_prompt(language, additional_instructions)
    
    gemini_file = None
    temp_file_to_delete = None
    original_filename = None # Initialize filename variable
    
    try:
        if source_type == "youtube":
            if not _is_youtube_url(source_value):
                raise ValueError(f"Invalid YouTube URL: {source_value}")
            
            # For YouTube URL, create content using from_uri
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(
                            file_uri=source_value,
                            mime_type="video/*", # Let Gemini infer video type
                        ),
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            logger.info("Prepared content using YouTube URI.")

        elif source_type == "google_drive":
            # Download the file first and get filename
            temp_file_path, original_filename = _download_google_drive_file(source_value)
            temp_file_to_delete = temp_file_path # Mark for deletion

            # Ensure the system's mimetypes library knows about .m4a before upload attempt
            mimetypes.add_type('audio/mp4', '.m4a')
            logger.info("Ensured .m4a MIME type ('audio/mp4') is registered.")

            # Upload the downloaded file to Gemini Files API
            logger.info(f"Uploading temporary file {temp_file_path} to Gemini...")
            try:
                # Upload without explicit mime_type, relying on internal guessing (helped by add_type)
                gemini_file = client.files.upload(file=temp_file_path)
                logger.info(f"File uploaded successfully to Gemini: {gemini_file.name} ({gemini_file.mime_type})")
            except ValueError as e: # Catch potential MIME type errors specifically
                 if "Unknown mime type" in str(e) or "Could not determine the mimetype" in str(e):
                     logger.error(f"Gemini file upload failed due to MIME type issue even after registration: {e}")
                     raise ValueError(f"Failed to upload file to Gemini due to MIME type issue: {e}")
                 else:
                     logger.error(f"Unexpected ValueError during Gemini file upload: {e}")
                     raise ValueError(f"Unexpected error uploading file to Gemini: {e}") # Re-raise other ValueErrors
            except Exception as e: # Catch other unexpected errors
                 logger.error(f"Unexpected error during Gemini file upload: {e}")
                 raise ValueError(f"Unexpected error uploading file to Gemini: {e}")

            # Wait for the file to be processed by Gemini
            while gemini_file.state == types.FileState.PROCESSING:
                logger.info("Waiting for Gemini file processing...")
                time.sleep(10) # Wait 10 seconds before checking again
                gemini_file = client.files.get(name=gemini_file.name)
            
            if gemini_file.state == types.FileState.FAILED:
                logger.error(f"Gemini file processing failed: {gemini_file.error}")
                raise ValueError(f"Gemini failed to process the uploaded file: {gemini_file.error}")
            elif gemini_file.state != types.FileState.ACTIVE:
                 logger.warning(f"Gemini file state is unexpected: {gemini_file.state}")
                 # Proceed anyway, maybe it works

            logger.info("Gemini file processing complete.")

            # Create content using the uploaded file reference
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(
                            file_uri=gemini_file.uri,
                            mime_type=gemini_file.mime_type # Use mime_type from the uploaded file object
                        ),
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            logger.info("Prepared content using uploaded Gemini file URI.")
            
        else:
            raise ValueError(f"Invalid source_type: {source_type}")

        # --- Token Counting (Optional - can be refined later) ---
        # logger.info("Counting tokens...") 
        # try:
        #     # Adapt token counting based on source type if needed
        #     token_count = client.models.count_tokens(model=base_model, contents=contents) 
        #     logger.info(f"Token count: {token_count}")
        # except Exception as e:
        #     logger.warning(f"Token counting failed: {str(e)}")
        #     logger.info("Continuing with analysis...")
            
        # --- Generate Content with Retry Logic ---
        logger.info(f"Getting structured analysis with model {base_model}...")
        response = None
        max_retries = 3
        initial_delay = 10 # seconds

        for attempt in range(max_retries):
            try:
                logger.info(f">>> Calling client.models.generate_content (Attempt {attempt + 1}/{max_retries})...")
                response = client.models.generate_content(
                    model=base_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ContentAnalysis
                    )
                )
                logger.info("<<< client.models.generate_content call successful.")
                break # Exit loop on success
            except google_genai_errors.ServerError as e:
                logger.warning(f"Attempt {attempt + 1} failed with ServerError: {e}")
                # Check if it's a 503 error and if we have retries left
                # Note: google.api_core.exceptions.ServiceUnavailable might also be relevant,
                # but the traceback showed google.genai.errors.ServerError
                # We access the status code via e.args if available, or check message
                status_code = getattr(e, 'status_code', None) # Prefer status_code if present
                is_503 = status_code == 503 or "503" in str(e) # Check status code or message

                if is_503 and attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    logger.info(f"Retrying after {delay} seconds due to 503 error...")
                    time.sleep(delay)
                else:
                    logger.error(f"Final attempt failed or non-retryable ServerError encountered.")
                    raise # Re-raise the last exception if retries exhausted or not 503
            except Exception as e: # Catch other potential errors during the call
                 logger.error(f"Unexpected error during generate_content call: {e}", exc_info=True)
                 raise # Re-raise other critical errors immediately
            finally:
                 # This log might be less useful here now with the loop logging
                 # logger.info("<<< client.models.generate_content call finished.")
                 pass # Keep finally for structure if needed later

        # --- Process Response ---
        analysis_result = None
        if response: # Only proceed if response was successfully obtained
            raw_response_text = response.text # Store original response

            # 1. Attempt deterministic cleaning and parsing first
            logger.info("Attempting deterministic JSON cleaning and parsing...")
            cleaned_json = _clean_and_parse_json(raw_response_text)

            if cleaned_json:
                logger.info("Deterministic cleaning successful. Validating with Pydantic...")
                try:
                    # Validate against the Pydantic model
                    content_analysis = ContentAnalysis.model_validate(cleaned_json)
                    logger.info("Cleaned JSON successfully validated with Pydantic model.")
                    analysis_result = cleaned_json # Use the validated JSON
                except Exception as pydantic_error: # Catch Pydantic validation errors
                    logger.warning(f"Pydantic validation failed after deterministic cleaning: {pydantic_error}")
                    # Proceed to LLM fix attempt if validation fails

            # 2. If deterministic cleaning/parsing/validation failed, try LLM fix
            if analysis_result is None:
                logger.warning("Deterministic JSON processing failed or validation failed. Attempting LLM fix...")
                fixed_json = _fix_json_with_gemini(client, raw_response_text) # Use original text
                if fixed_json:
                    # Pydantic validation already happened inside _fix_json_with_gemini
                    logger.info("LLM JSON fix successful and validated!")
                    analysis_result = fixed_json
                else:
                    logger.error("LLM fix attempt also failed.")
                    # Fall through to return error structure

        # 3. Return result or error
        if analysis_result:
            return {
                'analysis': analysis_result,
                'original_filename': original_filename,
                'google_drive_id': source_value if source_type == 'google_drive' else None
            }
        else:
            logger.error("Failed to obtain valid JSON after all attempts. Returning error.")
            return {
                'analysis': {"error": "Failed to parse, fix, or validate JSON response from Gemini", "raw_response": raw_response_text},
                'original_filename': original_filename,
                'google_drive_id': source_value if source_type == 'google_drive' else None
            }

    except google_exceptions.GoogleAPIError as e:
        logger.error(f"Gemini API error during analysis: {e}")
        # Provide more specific feedback if possible
        if "API key not valid" in str(e):
             raise ValueError("Invalid Gemini API Key provided.")
        elif "quota" in str(e).lower():
             raise ValueError("Gemini API quota exceeded.")
        else:
             raise ValueError(f"Gemini API error: {e}")
    except Exception as e:
        logger.error(f"Error analyzing {source_type} source: {str(e)}", exc_info=True)
        raise # Re-raise other exceptions to be caught by main.py

    finally:
        # --- Cleanup ---
        # Delete the temporary file if it was created
        if temp_file_to_delete and os.path.exists(temp_file_to_delete):
            try:
                # Get the directory containing the temp file
                temp_dir = os.path.dirname(temp_file_to_delete)
                shutil.rmtree(temp_dir) # Remove the whole directory
                logger.info(f"Successfully deleted temporary directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Error deleting temporary directory {temp_dir}: {e}")
        
        # Delete the file from Gemini Files API if it was uploaded
        if gemini_file:
            try:
                logger.info(f"Deleting Gemini file: {gemini_file.name}")
                client.files.delete(name=gemini_file.name)
                logger.info(f"Successfully deleted Gemini file: {gemini_file.name}")
            except Exception as e:
                # Log error but don't fail the whole request because of cleanup issue
                logger.error(f"Error deleting Gemini file {gemini_file.name}: {e}")


def _fix_json_with_gemini(client, response_text: str, max_attempts: int = 3) -> Optional[Dict[str, Any]]:
    """
    Attempts to fix malformed JSON using the designated fix model.
    
    Args:
        client: Gemini API client
        response_text (str): The original malformed JSON text
        max_attempts (int): Maximum number of fix attempts
        
    Returns:
        dict: Fixed and parsed JSON if successful, None otherwise
    """
    for attempt in range(max_attempts):
        try:
            logger.info(f"Fix attempt {attempt+1}/{max_attempts}...")
            
            # Prompt Gemini to fix only the JSON format
            fix_prompt = f"""The following text is supposed to be a JSON object matching a specific Pydantic schema, but it's malformed. Please fix ONLY the JSON formatting issues (e.g., missing commas, quotes, brackets) and return ONLY the corrected JSON object. Do not add, remove, or change any data values. Do not include any explanatory text or markdown formatting.

Malformed JSON:
```json
{response_text}
```"""
            
            logger.info(f"Sending malformed JSON to {fix_model} for fixing...")
            # Get fixed JSON from Gemini
            fix_response = client.models.generate_content(
                model=fix_model,
                contents=[{"role": "user", "parts": [{"text": fix_prompt}]}],
                 # Ensure the fix model also returns JSON
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            # Apply deterministic cleaning to the fix model's output
            logger.info("Applying deterministic cleaning to the fix model's output...")
            cleaned_fixed_json = _clean_and_parse_json(fix_response.text)

            if cleaned_fixed_json:
                logger.info("Cleaned fix output successfully parsed. Validating with Pydantic...")
                # Validate against the Pydantic model
                content_analysis = ContentAnalysis.model_validate(cleaned_fixed_json)
                logger.info("Fixed and cleaned JSON successfully validated with Pydantic model.")
                return cleaned_fixed_json # Return the validated dictionary
            else:
                 logger.warning(f"Attempt {attempt+1} - Could not parse JSON even after cleaning the fix model's output.")
                 # Continue to next attempt if parsing failed after cleaning

        except json.JSONDecodeError as e: # This might now be less likely if _clean_and_parse_json handles it
            logger.warning(f"Attempt {attempt+1} - JSON parsing error during fix: {str(e)}")
            # If parsing fails even after cleaning, continue to the next attempt
        except Exception as e: # Catches Pydantic validation errors and others
            logger.warning(f"Attempt {attempt+1} - Validation or other error after fix attempt: {str(e)}")
            # Don't retry if validation fails, the content is likely wrong, exit the loop
            break

    # If the loop completes without returning a validated JSON, it means all attempts failed
    logger.error("All fix attempts failed or validation failed.")
    return None
