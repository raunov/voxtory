import json
import os
import threading
import time
import uuid
import asyncio
import traceback
import requests
import logging
from datetime import datetime

from poc import generate
import db
from config import POLL_INTERVAL, MAX_RETRIES, RETRY_DELAY

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('worker')

# Global flag to control the worker thread
running = True

def send_webhook(webhook_url, job_data, attempt=1):
    """Send webhook notification with retry logic"""
    if not webhook_url:
        return True
        
    try:
        response = requests.post(
            webhook_url,
            json=job_data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code >= 200 and response.status_code < 300:
            print(f"Webhook sent successfully to {webhook_url}")
            return True
        else:
            print(f"Webhook failed with status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Webhook error: {str(e)}")
    
    # Retry logic
    if attempt < MAX_RETRIES:
        print(f"Retrying webhook in {RETRY_DELAY} seconds (attempt {attempt+1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY)
        return send_webhook(webhook_url, job_data, attempt + 1)
    else:
        print(f"Webhook failed after {MAX_RETRIES} attempts")
        return False

# Dictionary to temporarily store API keys for jobs in progress
# This avoids storing API keys in the database
_job_api_keys = {}

def set_job_api_key(job_id, api_key):
    """Store an API key for a job temporarily"""
    _job_api_keys[job_id] = api_key

def get_job_api_key(job_id):
    """Get the API key for a job"""
    return _job_api_keys.get(job_id)

def clear_job_api_key(job_id):
    """Remove an API key after job is processed"""
    if job_id in _job_api_keys:
        del _job_api_keys[job_id]

def process_job(job):
    """Process a single job"""
    job_id = job['id']
    file_path = job['file_path']
    webhook_url = job['webhook_url']
    
    logger.info(f"Processing job {job_id} for file {file_path}")
    
    # Update job status to processing
    db.update_job_status(job_id, "processing")
    
    try:
        # Retrieve the API key for this job
        api_key = get_job_api_key(job_id)
        if not api_key:
            # Fall back to environment variable if no job-specific key
            api_key = os.environ.get("GEMINI_API_KEY")
            logger.info(f"Using environment API key for job {job_id}")
        else:
            logger.info(f"Using job-specific API key for job {job_id}")
            
        # Check if file exists before processing
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found at {file_path}")
            
        # Log file information
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        logger.info(f"File size: {file_size} bytes, Path: {file_path}")
        
        # Set up a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Call the generate function from poc.py with the API key
            logger.info(f"Starting Gemini API processing for job {job_id}")
            results = generate(file_path, api_key=api_key)
            logger.info(f"Gemini API processing completed for job {job_id}")
        except Exception as api_error:
            # Get full traceback for API errors
            error_traceback = traceback.format_exc()
            logger.error(f"Gemini API error: {str(api_error)}\n{error_traceback}")
            raise
        finally:
            # Clean up the event loop
            loop.close()
        
        # Verify we got valid results
        if isinstance(results, str):
            logger.warning(f"Results not in JSON format: {results[:100]}...")
        
        # Update job status to completed with results
        updated_job = db.update_job_status(job_id, "completed", results=results)
        logger.info(f"Job {job_id} updated with completed status")
        
        # Send webhook if URL is provided
        if webhook_url:
            webhook_sent = send_webhook(webhook_url, updated_job)
            if not webhook_sent:
                logger.warning(f"Webhook notification failed for job {job_id}")
        
        # Clean up the uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File {file_path} removed after job completion")
            else:
                logger.warning(f"File {file_path} not found during cleanup")
        except Exception as e:
            logger.error(f"Error removing file {file_path}: {str(e)}")
            
        # Always clear the API key when done
        clear_job_api_key(job_id)
        
        logger.info(f"Job {job_id} completed successfully")
        return True
        
    except Exception as e:
        # Get full traceback
        error_traceback = traceback.format_exc()
        error_message = f"{str(e)}\n{error_traceback}"
        logger.error(f"Error processing job {job_id}: {str(e)}\n{error_traceback}")
        
        # Create a more detailed error message for the user
        user_error_message = str(e)
        if "Failed to convert server response to JSON" in user_error_message:
            user_error_message = "Failed to process Gemini API response. This could be due to a temporary issue with the Gemini API or an invalid response format. Please try again or check your input file format."
        elif "Could not determine the mimetype" in user_error_message:
            user_error_message = f"{user_error_message}. Try adding the mime_type parameter (e.g., video/mp4, audio/mpeg) when submitting the job."
        
        # Update job status to failed with detailed error message
        updated_job = db.update_job_status(job_id, "failed", error=user_error_message)
        logger.info(f"Job {job_id} updated with failed status")
        
        # Send webhook with failure notification if URL is provided
        if webhook_url:
            webhook_sent = send_webhook(webhook_url, updated_job)
            if not webhook_sent:
                logger.warning(f"Webhook notification failed for job {job_id}")
        
        # Clean up the uploaded file on failure too
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File {file_path} removed after job failure")
            else:
                logger.warning(f"File {file_path} not found during cleanup")
        except Exception as cleanup_error:
            logger.error(f"Error removing file {file_path}: {str(cleanup_error)}")
            
        # Always clear the API key when done
        clear_job_api_key(job_id)
        
        return False

def worker_thread():
    """Background thread that polls for pending jobs and processes them"""
    print("Worker thread started")
    
    while running:
        try:
            # Get pending jobs
            pending_jobs = db.get_pending_jobs()
            
            if pending_jobs:
                # Process the oldest pending job
                process_job(pending_jobs[0])
            else:
                # No pending jobs, sleep for a bit
                time.sleep(POLL_INTERVAL)
                
        except Exception as e:
            print(f"Worker thread error: {str(e)}")
            time.sleep(POLL_INTERVAL)
    
    print("Worker thread stopped")

def start_worker():
    """Start the worker thread"""
    thread = threading.Thread(target=worker_thread, daemon=True)
    thread.start()
    return thread

def stop_worker():
    """Stop the worker thread"""
    global running
    running = False
