import argparse
import base64
import json
import os
import time
import logging
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('poc')

# Load environment variables
load_dotenv()

def get_mime_type(file_path):
    """
    Determine MIME type based on file extension
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string or None if can't determine
    """
    ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
    
    mime_types = {
        # Audio formats
        'mp3': 'audio/mpeg',
        'm4a': 'audio/x-m4a',
        'wav': 'audio/wav',
        'aac': 'audio/aac',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        
        # Video formats
        'mp4': 'video/mp4',
        'mov': 'video/quicktime',
        'avi': 'video/x-msvideo',
        'mkv': 'video/x-matroska',
        'webm': 'video/webm',
        'flv': 'video/x-flv',
        'wmv': 'video/x-ms-wmv',
        
        # Other common formats
        'pdf': 'application/pdf',
        'txt': 'text/plain',
        'html': 'text/html'
    }
    
    return mime_types.get(ext)

def wait_for_file_active(client, file, max_wait=300, check_interval=5):
    """
    Wait for a file to become active, with timeout.
    
    Args:
        client: genai.Client instance
        file: The uploaded file object
        max_wait: Maximum wait time in seconds (default: 5 minutes)
        check_interval: Time between status checks in seconds
        
    Returns:
        The active file object or raises an exception if timeout or processing failure
    """
    start_time = time.time()
    while time.time() - start_time < max_wait:
        # Get the latest file status
        current_file = client.files.get(name=file.name)
        
        # Check if file is active
        if current_file.state == "ACTIVE":
            print(f"File {file.name} is now active and ready to use")
            return current_file
            
        # Check if file processing failed
        if current_file.state == "FAILED":
            error_msg = current_file.error.message if hasattr(current_file, 'error') else "Unknown error"
            raise Exception(f"File processing failed: {error_msg}")
            
        # Wait before checking again
        print(f"File {file.name} is still in {current_file.state} state. Waiting...")
        time.sleep(check_interval)
    
    # If we get here, we've timed out
    raise Exception(f"Timeout waiting for file {file.name} to become active")

def generate(file_path, output_file=None, api_key=None):
    """
    Generate content using Gemini API and ensure proper JSON formatting.
    
    Args:
        file_path: Path to the video file to analyze
        output_file: Optional path to save the JSON output
        api_key: Optional Gemini API key to use instead of environment variable
    """
    # Use provided API key or fall back to environment variable
    gemini_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("No Gemini API key provided")
    
    # Check file existence and size
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    logger.info(f"Processing file: {file_path} (Size: {file_size} bytes)")
        
    client = genai.Client(
        api_key=gemini_key,
    )

    # Determine MIME type based on file extension
    mime_type = get_mime_type(file_path)
    if not mime_type:
        logger.warning(f"Could not determine MIME type for {file_path}. Will attempt to detect automatically.")
        raise ValueError(f"Unknown mime type: Could not determine the mimetype for your file\n    please set the `mime_type` argument")
    
    logger.info(f"Using MIME type: {mime_type} for file: {file_path}")
    
    try:
        # Upload the file
        logger.info(f"Uploading file to Gemini API: {file_path}")
        uploaded_file = client.files.upload(file=file_path)
        logger.info(f"File uploaded successfully with ID: {uploaded_file.name}")
        
        # Wait for the file to become active
        logger.info(f"Waiting for file to be processed by Gemini API")
        active_file = wait_for_file_active(client, uploaded_file)
        logger.info(f"File is now active and ready for processing")
        
        files = [active_file]
        model = "gemini-2.0-flash-thinking-exp-01-21"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[0].uri,
                        mime_type=mime_type or files[0].mime_type,
                    ),
                    types.Part.from_text(text="""You are tasked with analyzing a video recording and creating transcript, summary and dossiers for each speaker mentioned.

Additional instructions for video content:

Include visual descriptions of scenes and actions where relevant

Note significant visual elements alongside the audio transcript

Identify speakers based on both visual and audio cues

Follow these instructions carefully:

Full transcript with timestamps

Key topics discussed (in original language of the audio)

Summary and overall insights (in original language of the audio)

Speaker identification based on what the speakers say about themselves or each other. Use every clue to identify speakers, including self-introductions, introductions by others, and references to past roles or affiliations.
If you are sure that speaker's name is not explicitly mentioned, you may use a generic descriptor that best fits their role (e.g., \"Interviewer\", \"Guest Expert\", \"Company CEO\").

For each identified speaker, extract factual background information about them from the transcript based on what themselves or other participants say. Output this in the original language of the audio.
Focus on:
a. Their full name
b. Current role and affiliation
c. Past roles and affiliations
d. Factual statements about themselves or factual statements others make about them
e. Views and beliefs they express (only if clearly stated as their own views)
f. If its a video, then include visual descriptions of the speaker. if its an audio, then include the speaker's voice description.

Organize the information for each speaker into a dossier, in the original language of the audio. Be sure to distinguish between facts and views/beliefs.

Format your response as a JSON object with the following structure:
{
\"topics\": [\"Topic 1\", \"Topic 2\", \"Topic 3\"],
\"summary\": \"Overall insights and summary\",
\"language\": \"main language spoken in the audio\",
\"speakers\": [
{
\"name\": \"Speaker full name or role descriptor\",
\"roles_affiliations\": [
{\"role\": \"Current role\", \"affiliation\": \"Current affiliation\"},
{\"role\": \"Past role 1\", \"affiliation\": \"Past affiliation 1\"}
],
\"facts\": [\"Fact 1 about the speaker\", \"Fact 2 about the speaker\"],
\"views_beliefs\": [\"View/belief 1\", \"View/belief 2\"],
\"visual_description\": \"Description of the speaker's appearance and actions\"
}
],
\"transcript\": [
{\"speaker\": \"Speaker full name\", \"timestamp\": \"00:00:00\", \"text\": \"Speaker's spoken words\"},
{\"speaker\": \"Speaker full name\", \"timestamp\": \"00:00:00\", \"text\": \"Speaker's spoken words\"}
]
}

Include only factual information in the \"facts\" array. Opinions or subjective statements should not be included here.

If a speaker expresses clear views or beliefs about themselves or their work, include these in the \"views_beliefs\" array.

If certain information is not available, omit those fields entirely.

Ensure that your final output contains only the JSON object described above, without any additional explanation or commentary.

Remember to focus on extracting and presenting factual information from the transcript. Do not include any speculative or inferred information.
Your goal is to create an accurate and objective dossier for each speaker based solely on the information provided in the transcript.
Output the result in the original language of the audio."""),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            temperature=0,
            top_p=0.95,
            top_k=64,
            max_output_tokens=65536,
            response_mime_type="text/plain",
        )

        # Collect the complete response instead of streaming directly to output
        logger.info("Generating response from Gemini API...")
        full_response = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            # Handle None values in chunk.text
            if chunk.text is not None:
                full_response += chunk.text
            print(".", end="", flush=True)
        print("\n")
        logger.info("Response generation completed, processing result...")
        
        # Log response length for debugging
        response_length = len(full_response)
        logger.info(f"Response length: {response_length} characters")
        
        # Save raw response for debugging
        raw_response_path = f"{os.path.splitext(file_path)[0]}_raw_response.txt"
        with open(raw_response_path, 'w', encoding='utf-8') as f:
            f.write(full_response)
        logger.info(f"Raw response saved to {raw_response_path}")
        
        # Ensure proper JSON formatting
        # Strip any text before the first '{'
        if '{' in full_response:
            json_start = full_response.find('{')
            if json_start > 0:
                logger.warning(f"Found {json_start} characters before JSON start, stripping them")
                full_response = full_response[json_start:]
        else:
            logger.error("No JSON object found in response (no opening '{' character)")
            raise ValueError("Response doesn't contain a JSON object")
        
        # Strip any text after the last '}'
        if '}' in full_response:
            json_end = full_response.rfind('}') + 1
            if json_end < len(full_response):
                logger.warning(f"Found {len(full_response) - json_end} characters after JSON end, stripping them")
                full_response = full_response[:json_end]
        else:
            logger.error("No JSON object end found in response (no closing '}' character)")
            raise ValueError("Response doesn't contain a complete JSON object")
        
        # Verify it's valid JSON
        try:
            json_data = json.loads(full_response)
            logger.info("Successfully parsed response as valid JSON")
            
            # Save to file if specified
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Output saved to {output_file}")
            
            # Print brief summary of the JSON data
            num_speakers = len(json_data.get('speakers', []))
            num_transcript_entries = len(json_data.get('transcript', []))
            logger.info(f"Extracted data: {num_speakers} speakers, {num_transcript_entries} transcript entries")
            
            return json_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response as JSON: {str(e)}")
            
            # Log more details about the parsing error
            error_position = e.pos
            context_start = max(0, error_position - 50)
            context_end = min(len(full_response), error_position + 50)
            error_context = full_response[context_start:context_end]
            
            logger.error(f"Error at position {error_position}: {error_context}")
            logger.error(f"Error details: {e.msg}")
            
            # Return the raw response for further debugging
            raise ValueError(f"Failed to convert server response to JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process a video file with Gemini API")
    parser.add_argument("file_path", help="Path to the video file to analyze")
    parser.add_argument("--output", "-o", help="Path to save JSON output")
    args = parser.parse_args()
    
    # Call generate with the file path and optional output file
    generate(args.file_path, args.output)
