import os
import re
import uuid
import requests
import yt_dlp
from urllib.parse import urlparse, parse_qs

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

def is_google_drive_url(url):
    """
    Check if the URL is a Google Drive URL
    
    Args:
        url: URL string to check
        
    Returns:
        bool: True if Google Drive URL, False otherwise
    """
    patterns = [
        r'^(https?://)?(www\.)?drive\.google\.com/file/d/.*',
        r'^(https?://)?(www\.)?drive\.google\.com/open\?id=.*',
        r'^(https?://)?(www\.)?docs\.google\.com/.*',
        # Add pattern for direct download URLs
        r'^(https?://)?(www\.)?drive\.google\.com/uc\?.*export=download.*&id=.*'
    ]
    
    for pattern in patterns:
        if re.match(pattern, url):
            return True
    
    return False

def extract_file_id_from_google_drive_url(url):
    """
    Extract the file ID from a Google Drive URL
    
    Args:
        url: Google Drive URL
        
    Returns:
        string: File ID or None if not found
    """
    # Handle /file/d/ format
    if '/file/d/' in url:
        # Extract the ID from a URL like https://drive.google.com/file/d/FILE_ID/view
        file_id = url.split('/file/d/')[1].split('/')[0]
        return file_id
    
    # Handle direct download URL with export=download&id= format
    if 'export=download' in url and 'id=' in url:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'id' in query_params:
            return query_params['id'][0]
    
    # Handle ?id= format (for open URLs)
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    if 'id' in query_params:
        return query_params['id'][0]
    
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

def is_valid_media_url(url):
    """
    Check if URL points to a supported media file
    
    Args:
        url: URL string to check
        
    Returns:
        bool: True if URL points to a supported media file
    """
    # Get file extension
    ext = get_file_extension_from_url(url)
    
    # List of supported media extensions
    media_extensions = ['mp4', 'avi', 'mov', 'mp3', 'm4a', 'wav', 'mkv', 'webm']
    
    # Check if extension is in supported list
    if ext and ext in media_extensions:
        return True
    
    # For URLs without extensions, try HEAD request to check content type
    try:
        response = requests.head(url, timeout=10)
        content_type = response.headers.get('Content-Type', '')
        
        # Check if content type is a media type
        media_types = ['video/', 'audio/']
        return any(media_type in content_type for media_type in media_types)
    except Exception:
        # If HEAD request fails, we can't determine if it's valid
        return False

def download_youtube_video(url, output_dir):
    """
    Download YouTube video
    
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
            # The actual file path might be different from what we specified
            # due to yt-dlp's handling of formats and extensions
            return os.path.join(output_dir, filename)
    except Exception as e:
        raise Exception(f"YouTube download failed: {str(e)}")

def download_google_drive_file(url, output_dir):
    """
    Download file from Google Drive
    
    Args:
        url: Google Drive URL
        output_dir: Directory to save the file
        
    Returns:
        string: Path to the downloaded file
    """
    try:
        # Extract the file ID from the URL
        file_id = extract_file_id_from_google_drive_url(url)
        if not file_id:
            raise Exception("Could not extract file ID from Google Drive URL")
        
        # Determine if this is already a direct download URL
        is_direct_download = 'export=download' in url and 'drive.google.com/uc' in url
        
        # Construct the direct download URL if needed
        if is_direct_download:
            download_url = url  # Use the provided URL as it's already a direct download link
        else:
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # First request to get cookies and confirm download
        session = requests.Session()
        response = session.get(download_url, stream=True, timeout=60)
        
        # Check if there's a download warning (for large files)
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                # Add confirmation parameter
                download_url = f"{download_url}&confirm={value}"
                response = session.get(download_url, stream=True, timeout=60)
                break
        
        # Generate a unique filename with UUID
        # Try to get original filename from Content-Disposition header
        content_disposition = response.headers.get('Content-Disposition')
        filename = None
        
        if content_disposition:
            # Extract filename from Content-Disposition
            matches = re.findall(r'filename="(.+?)"', content_disposition)
            if matches:
                filename = matches[0]
        
        # If filename not found, generate one based on content type
        if not filename:
            content_type = response.headers.get('Content-Type', '')
            ext = 'mp4'  # Default to mp4 for video/media files
            
            if 'audio/mpeg' in content_type:
                ext = 'mp3'
            elif 'audio/mp4' in content_type:
                ext = 'm4a'
            elif 'audio/wav' in content_type:
                ext = 'wav'
            elif 'video/quicktime' in content_type:
                ext = 'mov'
            
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
        raise Exception(f"Google Drive download failed: {str(e)}")

def download_media_file(url, output_dir):
    """
    Download media file from URL
    
    Args:
        url: Direct URL to media file
        output_dir: Directory to save the file
        
    Returns:
        string: Path to the downloaded file
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url, stream=True, timeout=60)
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
            
            # Generate unique filename with UUID and appropriate extension
            filename = f"{str(uuid.uuid4())}.{ext}"
        
        # Create full output path
        output_path = os.path.join(output_dir, filename)
        
        # Save the file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    except Exception as e:
        raise Exception(f"Media download failed: {str(e)}")

def download_from_url(url, output_dir):
    """
    Download media from URL (YouTube, Google Drive, or direct media)
    
    Args:
        url: URL to download from
        output_dir: Directory to save the file
        
    Returns:
        string: Path to the downloaded file
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine URL type and download accordingly
    if is_youtube_url(url):
        return download_youtube_video(url, output_dir)
    elif is_google_drive_url(url):
        return download_google_drive_file(url, output_dir)
    elif is_valid_media_url(url):
        return download_media_file(url, output_dir)
    else:
        raise Exception("URL is not a supported YouTube, Google Drive, or media URL")
