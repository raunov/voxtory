import os
import tempfile
import time
from typing import Dict, Any, Optional

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, BackgroundTasks, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT, MAX_FILE_SIZE, logger, ENVIRONMENT, CORS_ORIGINS
from auth import check_rate_limit
from gemini_client import GeminiClient
from job_store import JobStore
from gdrive_utils import download_gdrive_file

# Log startup information
logger.info(f"Starting Voxtory API in {ENVIRONMENT} environment")

# Initialize FastAPI app
app = FastAPI(
    title="Voxtory API",
    description="API for analyzing audio files from events and meetings using Google Gemini",
    version="1.0.0"
)

# Add CORS middleware with environment-specific settings
allowed_origins = CORS_ORIGINS.split(",") if CORS_ORIGINS else ["*"]
logger.info(f"CORS allowed origins: {allowed_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if ENVIRONMENT == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"] if ENVIRONMENT == "production" else ["*"],
    allow_headers=["X-API-Key", "Content-Type"] if ENVIRONMENT == "production" else ["*"],
)

# Mount static files for test interface
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Gemini client
gemini_client = GeminiClient()

# Initialize job store for async processing
job_store = JobStore()

# Background task function for processing audio files
async def process_audio_job(job_id: str, file_path: str, content_type: str):
    """Process an audio analysis job in the background."""
    try:
        # Update job status
        job_store.update_job(job_id, status="processing")
        logger.info(f"Processing job {job_id}")
        
        # Load the audio file
        with open(file_path, "rb") as file:
            audio_data = file.read()
        
        # Process with Gemini API
        result = gemini_client.analyze_audio(audio_data, content_type)
        
        # Check for errors
        if "error" in result:
            logger.error(f"Gemini API error for job {job_id}: {result['error']}")
            job_store.update_job(
                job_id, 
                status="failed",
                error=result["error"]
            )
        else:
            # Update job with success
            logger.info(f"Completed job {job_id} successfully")
            job_store.update_job(
                job_id, 
                status="completed",
                result=result["result"]
            )
    
    except Exception as e:
        # Handle any exceptions
        logger.error(f"Error processing job {job_id}: {str(e)}")
        job_store.update_job(
            job_id, 
            status="failed",
            error=str(e)
        )
    
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up temporary file for job {job_id}")
        except Exception as e:
            logger.error(f"Error removing temp file for job {job_id}: {str(e)}")

@app.get("/")
async def read_root():
    """Serves the test interface HTML file."""
    return FileResponse("static/index.html")

@app.get("/api/status")
async def status_check(api_key: str = Depends(check_rate_limit)) -> Dict[str, str]:
    """
    Check the API status and validate authentication.
    
    This endpoint can be used to verify that the API is running
    and that the provided API key is valid.
    """
    return {
        "status": "ok",
        "message": "API is running and authentication is valid",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.post("/api/analyze")
async def analyze_audio(
    audiofile: UploadFile = File(...),
    api_key: str = Depends(check_rate_limit)
) -> Dict[str, Any]:
    """
    Analyze an audio file using Google Gemini API.
    
    This endpoint accepts an audio file upload, sends it to the Gemini API
    for analysis, and returns the results.
    
    - **audiofile**: The audio file to analyze (required)
    """
    # Validate content type
    content_type = audiofile.content_type or "audio/mpeg"
    if not content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File must be an audio file"
        )
    
    # Read file content
    temp_file_path = None
    try:
        file_data = await audiofile.read()
        file_size = len(file_data)
        
        # Check file size (200MB limit)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)}MB)"
            )
        
        # Store in temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_data)
            temp_file_path = temp_file.name
        
        # Process the audio with Gemini API
        logger.info(f"Processing audio file: {audiofile.filename}, size: {file_size / (1024 * 1024):.2f} MB")
        analysis_result = gemini_client.analyze_audio(file_data, content_type)
        
        # Check for errors
        if "error" in analysis_result:
            logger.error(f"Error from Gemini API: {analysis_result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=analysis_result['error']
            )
        
        # Return result
        return analysis_result
    
    except Exception as e:
        # Handle exceptions not caught by specific handlers
        if isinstance(e, HTTPException):
            raise e
        
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )
    finally:
        # Always clean up temp file, even if an exception occurs
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temporary file: {cleanup_error}")

@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_handler(request, exc):
    """Handler for 404 errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "The requested resource was not found"}
    )

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    No authentication required.
    """
    try:
        # Simple health status
        return {
            "status": "healthy",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.post("/api/jobs")
async def create_analysis_job(
    background_tasks: BackgroundTasks,
    audiofile: UploadFile = File(...),
    api_key: str = Depends(check_rate_limit)
) -> Dict[str, Any]:
    """
    Create a new asynchronous audio analysis job.
    
    This endpoint accepts an audio file upload and starts processing in the background.
    It returns a job ID that can be used to check the status and retrieve results later.
    
    - **audiofile**: The audio file to analyze (required)
    """
    # Validate content type
    content_type = audiofile.content_type or "audio/mpeg"
    if not content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File must be an audio file"
        )
    
    # Read file content
    temp_file_path = None
    try:
        file_data = await audiofile.read()
        file_size = len(file_data)
        
        # Check file size (200MB limit)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)}MB)"
            )
        
        # Store in temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_data)
            temp_file_path = temp_file.name
        
        # Create a job
        job_id = job_store.create_job(
            file_path=temp_file_path,
            filename=audiofile.filename,
            content_type=content_type,
            file_size=file_size
        )
        
        # Start background task
        background_tasks.add_task(
            process_audio_job,
            job_id=job_id,
            file_path=temp_file_path,
            content_type=content_type
        )
        
        logger.info(f"Created job {job_id} for audio file: {audiofile.filename}")
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Job created successfully",
            "check_url": f"/api/jobs/{job_id}"
        }
    
    except Exception as e:
        # Clean up temp file if job creation fails
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temporary file: {cleanup_error}")
        
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating job: {str(e)}"
        )

@app.get("/api/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    api_key: str = Depends(check_rate_limit)
) -> Dict[str, Any]:
    """
    Get the status of an analysis job.
    
    This endpoint returns the current status of a job and its results if completed.
    
    - **job_id**: The ID of the job to check
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    response = {
        "job_id": job_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"]
    }
    
    # Include additional information based on status
    if job.get("filename"):
        response["filename"] = job["filename"]
    
    if job.get("file_size"):
        response["file_size"] = job["file_size"]
    
    # Include result if job is completed
    if job["status"] == "completed" and "result" in job:
        response["result"] = job["result"]
    
    # Include error if job failed
    if job["status"] == "failed" and "error" in job:
        response["error"] = job["error"]
    
    return response

@app.post("/api/analyze/gdrive")
async def analyze_gdrive_audio(
    file_id: str = Form(...),
    api_key: str = Depends(check_rate_limit)
) -> Dict[str, Any]:
    """
    Analyze an audio file from Google Drive using the Gemini API.
    
    This endpoint accepts a Google Drive file ID, downloads the file,
    and sends it to the Gemini API for analysis.
    
    - **file_id**: The Google Drive file ID (required)
    """
    try:
        # Download file from Google Drive
        file_data, content_type, error = await download_gdrive_file(file_id)
        
        # Handle download errors
        if error:
            logger.error(f"Error downloading Google Drive file: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        # Process the audio with Gemini API
        filename = f"gdrive_{file_id}"
        logger.info(f"Processing Google Drive audio file: {filename}, size: {len(file_data) / (1024 * 1024):.2f} MB")
        analysis_result = gemini_client.analyze_audio(file_data, content_type)
        
        # Check for errors
        if "error" in analysis_result:
            logger.error(f"Error from Gemini API: {analysis_result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=analysis_result['error']
            )
        
        # Return result
        return analysis_result
        
    except Exception as e:
        # Handle exceptions not caught by specific handlers
        if isinstance(e, HTTPException):
            raise e
        
        logger.error(f"Error processing Google Drive file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

@app.post("/api/jobs/gdrive")
async def create_gdrive_analysis_job(
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    api_key: str = Depends(check_rate_limit)
) -> Dict[str, Any]:
    """
    Create a new asynchronous audio analysis job for a Google Drive file.
    
    This endpoint accepts a Google Drive file ID, downloads the file,
    and starts processing in the background. It returns a job ID that
    can be used to check the status and retrieve results later.
    
    - **file_id**: The Google Drive file ID (required)
    """
    temp_file_path = None
    try:
        # Download file from Google Drive
        file_data, content_type, error = await download_gdrive_file(file_id)
        
        # Handle download errors
        if error:
            logger.error(f"Error downloading Google Drive file: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        # Store in temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_data)
            temp_file_path = temp_file.name
        
        # Create a job
        filename = f"gdrive_{file_id}"
        file_size = len(file_data)
        
        job_id = job_store.create_job(
            file_path=temp_file_path,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            source="gdrive",
            gdrive_id=file_id
        )
        
        # Start background task
        background_tasks.add_task(
            process_audio_job,
            job_id=job_id,
            file_path=temp_file_path,
            content_type=content_type
        )
        
        logger.info(f"Created job {job_id} for Google Drive file: {file_id}")
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Job created successfully",
            "check_url": f"/api/jobs/{job_id}"
        }
        
    except Exception as e:
        # Clean up temp file if job creation fails
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temporary file: {cleanup_error}")
        
        # Handle exceptions not caught by specific handlers
        if isinstance(e, HTTPException):
            raise e
            
        logger.error(f"Error creating job for Google Drive file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating job: {str(e)}"
        )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Generic exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": f"An unexpected error occurred: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
