import os
import httpx
import tempfile
from typing import Tuple, Optional
from config import logger, MAX_FILE_SIZE

async def download_gdrive_file(file_id: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """
    Download a file from Google Drive using its file ID.
    
    Args:
        file_id: The Google Drive file ID
    
    Returns:
        Tuple containing:
        - File content as bytes or None if download failed
        - File MIME type or None if download failed
        - Error message or None if download succeeded
    """
    # Google Drive direct download URL format
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        logger.info(f"Downloading file from Google Drive with ID: {file_id}")
        
        # Use httpx for async HTTP requests
        async with httpx.AsyncClient(timeout=60.0) as client:  # 60 second timeout
            # First make a HEAD request to check content type and size
            head_response = await client.head(url, follow_redirects=True)
            head_response.raise_for_status()
            
            # Check if it's an audio file
            content_type = head_response.headers.get('content-type', '')
            if not content_type.startswith('audio/'):
                logger.warning(f"File with ID {file_id} is not an audio file: {content_type}")
                return None, None, f"File is not an audio file (content type: {content_type})"
            
            # Check file size if available
            content_length = head_response.headers.get('content-length')
            if content_length and int(content_length) > MAX_FILE_SIZE:
                logger.warning(f"File with ID {file_id} exceeds maximum size: {int(content_length) // (1024 * 1024)} MB")
                return None, None, f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)}MB)"
            
            # Download the file
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            # Final check on content type from actual download
            final_content_type = response.headers.get('content-type', content_type)
            
            # Check actual file size
            content = response.content
            if len(content) > MAX_FILE_SIZE:
                logger.warning(f"Downloaded file exceeds maximum size: {len(content) // (1024 * 1024)} MB")
                return None, None, f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)}MB)"
            
            logger.info(f"Successfully downloaded file from Google Drive: {len(content) // 1024} KB, type: {final_content_type}")
            return content, final_content_type, None
            
    except httpx.RequestError as e:
        logger.error(f"Error downloading file from Google Drive: {str(e)}")
        return None, None, f"Network error: {str(e)}"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.error(f"File not found: {file_id}")
            return None, None, "File not found or not accessible"
        else:
            logger.error(f"HTTP error downloading file: {e.response.status_code}")
            return None, None, f"HTTP error: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Unexpected error downloading file: {str(e)}")
        return None, None, f"Error: {str(e)}"
