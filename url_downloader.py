import os
import re
import uuid
import requests
import logging
import yt_dlp
from urllib.parse import urlparse, parse_qs

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('url_downloader')

def is_google_drive_url(url):
    """
    Check if the URL is a Google Drive URL
    
    Args:
        url: URL string to check
        
    Returns:
        bool: True if Google Drive URL, False otherwise
    """
    patterns = [
        r'^https://drive\.google\.com/file/d/([^/]+)',
        r'^https://drive\.google\.com/open\?id=([^/&]+)',
        r'^https://drive\.google\.com/uc\?.*id=([^/&]+)'
    ]
    
    for pattern in patterns:
        if re.search(pattern, url):
            return True
    
    return False

def extract_google_drive_file_id(url):
    """
    Extract the file ID from a Google Drive URL
    
    Args:
        url: Google Drive URL
        
    Returns:
        string: File ID or None if not found
    """
    # Handle 'file/d/' format
    match = re.search(r'drive\.google\.com/file/d/([^/]+)', url)
    if match:
        return match.group(1)
    
    # Handle '?id=' format
    match = re.search(r'id=([^&]+)', url)
    if match:
        return match.group(1)
    
    return None

def get_file_extension_from_url(url):
    """
    Extract file extension from URL
    
    Args:
        url: URL of the file
        
    Returns:
        string: File extension or None if no extension found
    """
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Extract extension from path
    if '.' in path:
        return path.split('.')[-1].lower()
    
    return None

def is_youtube_url(url):
    """
    Check if the URL is a YouTube URL
    
    Args:
        url: URL string to check
        
    Returns:
        bool: True if YouTube URL, False otherwise
    """
    # Regular expression patterns for various YouTube URL formats
    patterns = [
        r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$',
        r'^(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^(https?://)?(www\.)?youtu\.be/[\w-]+',
    ]
    
    for pattern in patterns:
        if re.match(pattern, url):
            return True
    
    return False

def download_youtube_video(url, output_dir):
    """
    Download YouTube video using yt-dlp
    
    Args:
        url: YouTube URL
        output_dir: Directory to save the video
        
    Returns:
        string: Path to the downloaded file
    """
    # Generate a unique filename with UUID
    filename = f"{str(uuid.uuid4())}.mp4"
    output_path = os.path.join(output_dir, filename)
    
    # yt-dlp options
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # Prefer MP4 format
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return os.path.join(output_dir, filename)
    except Exception as e:
        raise Exception(f"YouTube download failed: {str(e)}")

def download_file(url, output_dir):
    """
    Download file from any URL
    
    Args:
        url: URL to download from
        output_dir: Directory to save the file
        
    Returns:
        string: Path to the downloaded file
    """
    try:
        # Send a GET request to the URL
        session = requests.Session()
        response = session.get(url, stream=True, timeout=60)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Try to get the filename from Content-Disposition header
        content_disposition = response.headers.get('Content-Disposition')
        filename = None
        
        if content_disposition:
            # Extract filename from Content-Disposition
            matches = re.findall(r'filename="(.+?)"', content_disposition)
            if matches:
                filename = matches[0]
        
        # If filename not found in header, extract from URL
        if not filename:
            parsed_url = urlparse(url)
            path = parsed_url.path
            filename = os.path.basename(path)
        
        # If still no filename or it has no extension, generate one
        if not filename or '.' not in filename:
            # Try to determine extension from Content-Type
            content_type = response.headers.get('Content-Type', '')
            ext = 'mp4'  # Default to mp4
            
            if 'audio/mpeg' in content_type:
                ext = 'mp3'
            elif 'audio/mp4' in content_type:
                ext = 'm4a'
            elif 'audio/wav' in content_type:
                ext = 'wav'
            elif 'video/quicktime' in content_type:
                ext = 'mov'
            elif 'application/octet-stream' in content_type:
                ext = 'mp4'  # Default binary data to mp4
            elif 'video/' in content_type:
                ext = 'mp4'
            elif 'audio/' in content_type:
                ext = 'mp3'
            else:
                ext = 'mp4'  # Default unknown content to mp4
            
            # Generate unique filename with UUID and appropriate extension
            filename = f"{str(uuid.uuid4())}.{ext}"
        
        # Create full output path
        output_path = os.path.join(output_dir, filename)
        
        # Save the file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
        
        return output_path
    except Exception as e:
        raise Exception(f"File download failed: {str(e)}")

def download_from_google_drive(url, output_dir):
    """
    Download file from Google Drive
    
    Args:
        url: Google Drive URL
        output_dir: Directory to save the file
        
    Returns:
        string: Path to the downloaded file
    """
    logger.info(f"Processing Google Drive URL: {url}")
    file_id = extract_google_drive_file_id(url)
    
    if not file_id:
        raise Exception(f"Could not extract file ID from Google Drive URL: {url}")
    
    logger.info(f"Extracted Google Drive file ID: {file_id}")
    
    # First request to get the download token
    session = requests.Session()
    
    # Construct direct download URL
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    logger.info(f"Initial download URL: {download_url}")
    
    # First request to get cookies and confirm token if needed
    response = session.get(download_url, stream=True)
    
    # Check if this is a large file that needs confirmation
    if "confirm=" in response.text:
        # Extract the confirmation token
        confirm_match = re.search(r'"downloadUrl":"([^"]+)', response.text)
        if confirm_match:
            confirm_url = confirm_match.group(1).replace('\\u003d', '=').replace('\\u0026', '&')
            logger.info(f"Found confirmation URL: {confirm_url}")
            # Use the extracted URL directly
            download_url = confirm_url
        else:
            # Fallback to adding confirm=t
            download_url = f"{download_url}&confirm=t"
            logger.info(f"Using fallback confirmation URL: {download_url}")
    
    # Download with the updated URL or token
    response = session.get(download_url, stream=True)
    
    if response.status_code != 200:
        raise Exception(f"Failed to download from Google Drive. Status code: {response.status_code}")
    
    # Get content type to determine file extension
    content_type = response.headers.get('Content-Type', '')
    logger.info(f"Content-Type from Google Drive: {content_type}")
    
    # Attempt to get filename from Content-Disposition
    content_disposition = response.headers.get('Content-Disposition')
    filename = None
    
    if content_disposition:
        matches = re.findall(r'filename="(.+?)"', content_disposition)
        if matches:
            filename = matches[0]
            logger.info(f"Filename from Content-Disposition: {filename}")
    
    # If no filename found, generate one based on content type
    if not filename or '.' not in filename:
        ext = 'bin'  # Default extension for unknown types
        
        # Map content type to extension
        if 'audio/mpeg' in content_type:
            ext = 'mp3'
        elif 'audio/mp4' in content_type:
            ext = 'm4a'
        elif 'audio/wav' in content_type:
            ext = 'wav'
        elif 'video/mp4' in content_type:
            ext = 'mp4'
        elif 'video/quicktime' in content_type:
            ext = 'mov'
        elif 'video/x-msvideo' in content_type:
            ext = 'avi'
        elif 'video/x-matroska' in content_type:
            ext = 'mkv'
        elif 'application/octet-stream' in content_type:
            # For octet-stream, we'll try to be smart about audio/video
            # For simplicity, default to mp4 for now
            ext = 'mp4'
        
        # Generate unique filename with UUID
        filename = f"{str(uuid.uuid4())}.{ext}"
        logger.info(f"Generated filename based on content type: {filename}")
    
    # Create full output path
    output_path = os.path.join(output_dir, filename)
    logger.info(f"Saving Google Drive file to: {output_path}")
    
    # Save the file
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:  # Filter out keep-alive chunks
                f.write(chunk)
    
    logger.info(f"Successfully downloaded Google Drive file to: {output_path}")
    return output_path

def download_from_url(url, output_dir, mime_type=None):
    """
    Download file from any URL
    
    Args:
        url: URL to download from
        output_dir: Directory to save the file
        mime_type: Optional MIME type to specify for the file
        
    Returns:
        string: Path to the downloaded file, mime_type
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Processing download request for URL: {url}")
    
    try:
        # Special case for Google Drive URLs
        if is_google_drive_url(url):
            logger.info("Detected Google Drive URL")
            return download_from_google_drive(url, output_dir)
            
        # Special case for YouTube URLs
        elif is_youtube_url(url):
            logger.info("Detected YouTube URL")
            return download_youtube_video(url, output_dir)
        
        # For all other URLs, attempt direct download
        else:
            logger.info("Processing as standard direct download URL")
            return download_file(url, output_dir)
            
    except Exception as e:
        logger.error(f"Error downloading from URL: {str(e)}", exc_info=True)
        raise
