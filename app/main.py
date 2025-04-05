from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import json
from typing import Optional

from app.models import VideoAnalysisRequest, ApiResponse, ContentAnalysis
from app.auth import verify_api_key
from app.video_service import process_video
from app.utils.mermaid_generator import process_concept_map_to_mermaid_url
from app.utils.markdown_generator import process_content_analysis_to_markdown

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
    logger.info(f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
    return response

@app.get("/", tags=["Info"])
async def root():
    """Get API information"""
    return {
        "name": "Video Insights API",
        "version": "1.0.0",
        "description": "API for analyzing YouTube videos using Gemini AI",
        "endpoints": {
            "/analyze": "POST - Analyze a YouTube video",
            "/generate-mermaid": "POST - Generate a Mermaid mindmap from a concept map"
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
        # Input validation
        if not request.youtube_url and not request.google_drive_id:
            raise ValueError("Either 'youtube_url' or 'google_drive_id' must be provided.")
        if request.youtube_url and request.google_drive_id:
            raise ValueError("Provide either 'youtube_url' or 'google_drive_id', not both.")

        # Trim whitespace from inputs
        if request.youtube_url:
            request.youtube_url = request.youtube_url.strip()
            logger.info(f"Received request to analyze YouTube URL: {request.youtube_url}")
            source_type = "youtube"
            source_value = request.youtube_url
        else: # google_drive_id must be present due to validation above
            request.google_drive_id = request.google_drive_id.strip()
            logger.info(f"Received request to analyze Google Drive ID: {request.google_drive_id}")
            source_type = "google_drive"
            source_value = request.google_drive_id
            
        # Process the video/file
        result = process_video(
            source_value=source_value,
            source_type=source_type,
            language=request.language,
            api_key=api_key,
            additional_instructions=additional_instructions or ""
        )
        
        # If the result contains a concept_map, add mermaid data
        if result and "concept_map" in result:
            mermaid_data = process_concept_map_to_mermaid_url(result["concept_map"])
            result["mermaid"] = mermaid_data
            
        # Format the response according to the request
        if request.format == "json" or request.format == "both":
            # Keep the JSON result as is
            response_data = result
            
            # Add markdown if requested
            if request.format == "both":
                response_data["markdown"] = process_content_analysis_to_markdown(result)
        else:  # markdown only
            # Create a response with just the markdown
            markdown_content = process_content_analysis_to_markdown(result)
            response_data = {"markdown": markdown_content}
        
        # Return the result
        return ApiResponse(status="success", data=response_data)
        
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

@app.post("/generate-mermaid", tags=["Utilities"])
async def generate_mermaid(content_analysis: ContentAnalysis):
    """
    Generate a Mermaid mindmap from a concept map
    
    - **content_analysis**: The content analysis containing the concept map
    
    Returns:
        A dictionary with the mermaid code and URL
    """
    try:
        mermaid_data = process_concept_map_to_mermaid_url(content_analysis.concept_map)
        return {"status": "success", "data": mermaid_data}
    except Exception as e:
        logger.error(f"Error generating mermaid: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ApiResponse(status="error", error=f"Error generating mermaid: {str(e)}").model_dump()
        )
