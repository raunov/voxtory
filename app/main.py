from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import json
from typing import Optional

from app.models import VideoAnalysisRequest, ApiResponse
from app.auth import verify_api_key
from app.video_service import process_video

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Video Insights API",
    description="API for analyzing YouTube videos using Gemini AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Get client IP
    client_host = request.client.host if request.client else "unknown"
    
    # Log request
    # logger.info(f"Request started: {request.method} {request.url.path} from {client_host}")
    
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(f"Request completed: {request.method} {request.url.path} from {client_host} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
    return response

@app.get("/", tags=["Info"])
async def root():
    """Get API information"""
    return {
        "name": "Video Insights API",
        "version": "1.0.0",
        "description": "API for analyzing YouTube videos using Gemini AI",
        "endpoints": {
            "/analyze": "POST - Analyze a YouTube video"
        },
        "authentication": "Bring your own Gemini API key in X-Gemini-API-Key header"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok"}

@app.post("/analyze", response_model=ApiResponse, tags=["Analysis"])
async def analyze_video(
    request: VideoAnalysisRequest,
    api_key: str = Depends(verify_api_key),
    additional_instructions: Optional[str] = None
):
    """
    Analyze a YouTube video and extract insights.
    
    - **youtube_url**: The URL of the YouTube video to analyze
    - **language**: Language code for output (default: 'en' for English)
    - **additional_instructions**: Optional additional instructions for the prompt
    
    Requires Gemini API key in X-Gemini-API-Key header
    """
    try:
        # Trim whitespace from YouTube URL
        if request.youtube_url:
            request.youtube_url = request.youtube_url.strip()
            
        logger.info(f"Received request to analyze: {request.youtube_url}")
        
        # Process the video
        result = process_video(
            youtube_url=request.youtube_url,
            language=request.language,
            api_key=api_key,
            additional_instructions=additional_instructions or ""
        )
        
        # Return the result
        return ApiResponse(status="success", data=result)
        
    except ValueError as e:
        # Handle validation errors
        logger.warning(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400,
            content=ApiResponse(status="error", error=str(e)).model_dump()
        )
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Error processing video: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ApiResponse(status="error", error=f"Error processing video: {str(e)}").model_dump()
        )
