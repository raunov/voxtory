import base64
import json
import http.client
import re
from typing import Dict, Any, Optional

from config import (
    GEMINI_API_KEY,
    GEMINI_HOST,
    GEMINI_PATH,
    MODEL_NAME,
    logger
)


class GeminiClient:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self):
        """Initialize the Gemini client."""
        self.api_key = GEMINI_API_KEY
        self.host = GEMINI_HOST
        self.path = GEMINI_PATH
        self.model_name = MODEL_NAME
    
    def analyze_audio(self, audio_data: bytes, content_type: str) -> Dict[str, Any]:
        """
        Analyze audio data using the Gemini API.
        
        Args:
            audio_data: Binary audio data
            content_type: MIME type of the audio (e.g., 'audio/mpeg')
            
        Returns:
            Dict containing the analysis result or error information
        """
        logger.info("Analyzing audio with Gemini API")
        
        # Create a prompt for analysis
        prompt = """
You are tasked with analyzing an audio recording and creating transcript, summary and dossiers for each speaker mentioned. 
Follow these instructions carefully:

1. Full transcript with timestamps
2. Key topics discussed (in original language of the audio)
3. Summary and overall insights (in original language of the audio)

4. Speaker identification based on what the speakers say about themselves or each other. Use every clue to identify speakers, including self-introductions, introductions by others, and references to past roles or affiliations.
If you are sure that speaker's name is not explicitly mentioned, you may use a generic descriptor that best fits their role (e.g., "Interviewer", "Guest Expert", "Company CEO").

5. For each identified speaker, extract factual background information about them from the transcript based on what themselves or other participants say. Output this in the original language of the audio.
Focus on:
   a. Their full name 
   b. Current role and affiliation
   c. Past roles and affiliations
   d. Factual statements about themselves or factual statements others make about them
   e. Views and beliefs they express (only if clearly stated as their own views)

6. Organize the information for each speaker into a dossier, in the original language of the audio. Be sure to distinguish between facts and views/beliefs.

7. Format your response as a JSON object with the following structure:
   {
     "transcript": [
         {"speaker": "Speaker full name", "timestamp": "00:00:00", "text": "Speaker's spoken words"},
         {"speaker": "Speaker full name", "timestamp": "00:00:00", "text": "Speaker's spoken words"}
     ],
     "topics": ["Topic 1", "Topic 2", "Topic 3"],
     "summary": "Overall insights and summary",
     "language": "main language spoken in the audio",
     "speakers": [
       {
         "name": "Speaker full name or role descriptor",
         "roles_affiliations": [
           {"role": "Current role", "affiliation": "Current affiliation"},
           {"role": "Past role 1", "affiliation": "Past affiliation 1"}
         ],
         "facts": ["Fact 1 about the speaker", "Fact 2 about the speaker"],
         "views_beliefs": ["View/belief 1", "View/belief 2"]
       }
     ]
   }

9. Include only factual information in the "facts" array. Opinions or subjective statements should not be included here.

10. If a speaker expresses clear views or beliefs about themselves or their work, include these in the "views_beliefs" array.

11. If certain information is not available, omit those fields entirely.

12. Ensure that your final output contains only the JSON object described above, without any additional explanation or commentary.

Remember to focus on extracting and presenting factual information from the transcript. Do not include any speculative or inferred information. 
Your goal is to create an accurate and objective dossier for each speaker based solely on the information provided in the transcript.
Output the result in the original language of the audio.
        """
        
        # Encode audio data as base64
        encoded_audio = base64.b64encode(audio_data).decode('utf-8')
        
        # Prepare request payload with Google Search tool
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": content_type, "data": encoded_audio}}
                    ]
                }
            ],
            "tools": [
                {
                    "google_search": {}  # Enable Google Search tool
                }
            ]
        }
        
        return self._send_request(payload)
    
    def _extract_and_parse_json(self, text: str) -> Dict[str, Any]:
        """
        Extract and parse JSON from text, handling various formatting cases.
        
        Args:
            text: Text potentially containing JSON
            
        Returns:
            Dict with parsed JSON result or original text
        """
        # Log original text length for debugging
        logger.debug(f"Original text length: {len(text)}")
        
        # Strategy 1: Try to parse directly first
        try:
            json_obj = json.loads(text)
            logger.info("Successfully parsed text as JSON directly")
            return {"result": json_obj}
        except json.JSONDecodeError:
            logger.debug("Direct JSON parsing failed, trying alternative strategies")
        
        # Strategy 2: Try to extract JSON from markdown code blocks
        # Look for JSON in triple backtick code blocks
        json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(json_pattern, text)
        
        if matches:
            for json_str in matches:
                try:
                    # Try to parse each match
                    json_obj = json.loads(json_str.strip())
                    logger.info("Successfully extracted and parsed JSON from code block")
                    return {"result": json_obj}
                except json.JSONDecodeError:
                    continue
        
        # Strategy 3: Try to find JSON object by looking for curly braces
        try:
            # Find the first { and the last } in the text
            start_idx = text.find('{')
            if start_idx != -1:
                # Find the matching closing brace
                brace_count = 0
                json_text = ""
                
                for i in range(start_idx, len(text)):
                    char = text[i]
                    json_text += char
                    
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        
                    if brace_count == 0 and len(json_text) > 2:  # At least "{}"
                        try:
                            json_obj = json.loads(json_text)
                            logger.info("Successfully extracted and parsed JSON by brace matching")
                            return {"result": json_obj}
                        except json.JSONDecodeError:
                            # Keep trying with more text
                            pass
        except Exception as e:
            logger.warning(f"JSON extraction by brace matching failed: {str(e)}")
        
        # Strategy 4: Try to clean up the text and parse again
        try:
            # Remove any text before the first { and after the last }
            first_brace = text.find('{')
            last_brace = text.rfind('}')
            
            if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
                cleaned_text = text[first_brace:last_brace + 1]
                json_obj = json.loads(cleaned_text)
                logger.info("Successfully parsed JSON after cleaning text")
                return {"result": json_obj}
        except json.JSONDecodeError:
            logger.debug("JSON parsing failed after cleaning text")
        
        # If all strategies fail, return the original text
        logger.warning("All JSON parsing strategies failed, returning original text")
        return {"result": text}
    
    def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a request to the Gemini API.
        
        Args:
            payload: Request payload
            
        Returns:
            Dict containing the API response or error information
        """
        try:
            # Convert payload to JSON string
            payload_str = json.dumps(payload)
            
            # Create connection to Gemini API
            conn = http.client.HTTPSConnection(self.host)
            
            # Set headers with API key in header instead of URL for better security
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key  # Google API convention for API key
            }
            
            # Make request to Gemini API (without API key in URL)
            logger.info("Sending request to Gemini API")
            conn.request("POST", self.path, payload_str, headers)
            
            # Get response
            response = conn.getresponse()
            response_data = response.read().decode()
            logger.info(f"Received response from Gemini API. Status: {response.status}")
            
            # Check for successful response
            if response.status != 200:
                logger.error(f"Gemini API error: {response.status} - {response_data}")
                return {"error": f"Error from Gemini API: {response.status}", "details": response_data}
            
            # Parse response
            response_json = json.loads(response_data)
            
            # Extract the text from the response
            analysis_text = response_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            # Clean and parse the text to JSON
            return self._extract_and_parse_json(analysis_text)
            
        except Exception as e:
            logger.error(f"Error communicating with Gemini API: {str(e)}")
            return {"error": f"Error: {str(e)}"}
        finally:
            if 'conn' in locals():
                conn.close()
