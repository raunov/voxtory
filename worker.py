import json
import os
import threading
import time
import uuid
import requests
from datetime import datetime

from poc import generate
import db
from config import POLL_INTERVAL, MAX_RETRIES, RETRY_DELAY

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
    
    print(f"Processing job {job_id} for file {file_path}")
    
    # Update job status to processing
    db.update_job_status(job_id, "processing")
    
    try:
        # Retrieve the API key for this job
        api_key = get_job_api_key(job_id)
        if not api_key:
            # Fall back to environment variable if no job-specific key
            api_key = os.environ.get("GEMINI_API_KEY")
            
        # Call the generate function from poc.py with the API key
        results = generate(file_path, api_key=api_key)
        
        # Update job status to completed with results
        updated_job = db.update_job_status(job_id, "completed", results=results)
        
        # Send webhook if URL is provided
        if webhook_url:
            webhook_sent = send_webhook(webhook_url, updated_job)
            if not webhook_sent:
                print(f"Warning: Webhook notification failed for job {job_id}")
        
        # Clean up the uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"File {file_path} removed after job completion")
            else:
                print(f"File {file_path} not found during cleanup")
        except Exception as e:
            print(f"Error removing file {file_path}: {str(e)}")
            
        # Always clear the API key when done
        clear_job_api_key(job_id)
        
        print(f"Job {job_id} completed successfully")
        return True
        
    except Exception as e:
        error_message = str(e)
        print(f"Error processing job {job_id}: {error_message}")
        
        # Update job status to failed with error message
        updated_job = db.update_job_status(job_id, "failed", error=error_message)
        
        # Send webhook with failure notification if URL is provided
        if webhook_url:
            webhook_sent = send_webhook(webhook_url, updated_job)
            if not webhook_sent:
                print(f"Warning: Webhook notification failed for job {job_id}")
        
        # Clean up the uploaded file on failure too
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"File {file_path} removed after job failure")
            else:
                print(f"File {file_path} not found during cleanup")
        except Exception as cleanup_error:
            print(f"Error removing file {file_path}: {str(cleanup_error)}")
            
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
