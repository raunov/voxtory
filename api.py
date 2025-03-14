import json
import os
import uuid
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

import db
from worker import start_worker, stop_worker
from config import API_HOST, API_PORT, API_DEBUG, UPLOAD_FOLDER
from url_downloader import download_from_url

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max file size

# Initialize database
db.init_db()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mp3', 'm4a', 'wav', 'mkv'}

def verify_api_key(api_key):
    """Verify that the API key has a valid format for Gemini API"""
    # Basic validation - Gemini API keys typically start with "AI" and are 39 chars long
    # This is a simplified check - in production you'd want more robust validation
    if not api_key or not isinstance(api_key, str) or len(api_key) < 30:
        return False
    return True

def hash_api_key(api_key):
    """Create a partial hash of the API key for reference (first 8 chars only)"""
    if not api_key:
        return None
    # Only hash the first 8 characters to avoid storing sensitive data
    prefix = api_key[:8]
    return hashlib.sha256(prefix.encode()).hexdigest()

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/jobs', methods=['POST'])
def create_job():
    """Create a new job by uploading a file or providing a URL"""
    # Check for API key in header
    api_key = request.headers.get('X-Gemini-API-Key')
    if not api_key:
        return jsonify({"error": "Missing API key. Please provide X-Gemini-API-Key header"}), 401
    
    # Verify API key format
    if not verify_api_key(api_key):
        return jsonify({"error": "Invalid API key format"}), 401
    
    # Get a hash of the API key for storage
    api_key_hash = hash_api_key(api_key)
    
    # Get webhook URL if provided
    webhook_url = request.form.get('webhook_url')
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Check if URL was provided in the request
    url = request.form.get('url')
    
    # Process URL if provided
    if url:
        try:
            # Extract mime_type from form data if provided
            mime_type = request.form.get('mime_type')
            
            # Log the URL processing attempt
            print(f"Processing URL job for {url} with mime_type: {mime_type or 'auto-detect'}")
            
            # Download the file from URL with improved error handling
            try:
                file_path = download_from_url(url, app.config['UPLOAD_FOLDER'], mime_type)
                print(f"Downloaded file from URL to {file_path}")
            except Exception as e:
                error_msg = f"Failed to download file from URL: {str(e)}"
                print(f"Download error: {error_msg}")
                return jsonify({"error": error_msg}), 400
            
            # Store the API key for the worker to use
            from worker import set_job_api_key
            set_job_api_key(job_id, api_key)
            
            # Create job record in database with API key hash and source URL
            job = db.create_job(job_id, file_path, webhook_url, api_key_hash, url)
            
            return jsonify({
                "job_id": job_id,
                "status": job['status'],
                "message": "Job created successfully from URL"
            }), 201
            
        except Exception as e:
            error_msg = f"URL processing error: {str(e)}"
            print(f"URL processing error: {error_msg}")
            return jsonify({"error": error_msg}), 400
    
    # If no URL, check for file upload
    if 'file' not in request.files:
        return jsonify({"error": "No file or URL provided. Please upload a file or provide a 'url' parameter."}), 400
        
    file = request.files['file']
    
    # Check if file has a name
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    # Check if file has allowed extension
    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
    
    # Process uploaded file
    filename = secure_filename(file.filename)
    file_extension = filename.rsplit('.', 1)[1].lower()
    storage_filename = f"{job_id}.{file_extension}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], storage_filename)
    
    # Save the file
    file.save(file_path)
    
    # Store the API key for the worker to use
    from worker import set_job_api_key
    set_job_api_key(job_id, api_key)
    
    # Create job record in database with API key hash
    job = db.create_job(job_id, file_path, webhook_url, api_key_hash)
    
    return jsonify({
        "job_id": job_id,
        "status": job['status'],
        "message": "Job created successfully"
    }), 201

@app.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get a job by its ID"""
    # Check for API key in header
    api_key = request.headers.get('X-Gemini-API-Key')
    if not api_key:
        return jsonify({"error": "Missing API key. Please provide X-Gemini-API-Key header"}), 401
    
    # Verify API key format
    if not verify_api_key(api_key):
        return jsonify({"error": "Invalid API key format"}), 401
        
    job = db.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
        
    response = {
        "job_id": job['id'],
        "status": job['status'],
        "created_at": job['created_at'],
        "updated_at": job['updated_at']
    }
    
    # Include source URL if available
    if job.get('source_url'):
        response['source_url'] = job['source_url']
    
    # Include results if job is completed
    if job['status'] == 'completed' and job.get('results'):
        response['results'] = job['results']
        
    # Include error if job failed
    if job['status'] == 'failed' and job.get('error'):
        response['error'] = job['error']
        
    return jsonify(response)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Quick DB check - just verify we can connect
        db.get_db_connection().close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "version": "1.0.0"  # Version tracking
    }), 200

@app.route('/jobs', methods=['GET'])
def list_jobs():
    """List all jobs"""
    # Check for API key in header
    api_key = request.headers.get('X-Gemini-API-Key')
    if not api_key:
        return jsonify({"error": "Missing API key. Please provide X-Gemini-API-Key header"}), 401
    
    # Verify API key format
    if not verify_api_key(api_key):
        return jsonify({"error": "Invalid API key format"}), 401
        
    jobs = db.get_all_jobs()
    
    # Format the response
    job_list = []
    for job in jobs:
        job_data = {
            "job_id": job['id'],
            "status": job['status'],
            "created_at": job['created_at'],
            "updated_at": job['updated_at']
        }
        
        # Include source URL if available
        if job.get('source_url'):
            job_data['source_url'] = job['source_url']
        job_list.append(job_data)
        
    return jsonify({"jobs": job_list})

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({"error": "File too large"}), 413

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server error"""
    return jsonify({"error": "Internal server error"}), 500

# Worker thread
worker_thread = None

# Start worker thread for processing jobs
worker_thread = start_worker()

def start_api():
    """Start the Flask API server (for local development)"""
    # Start Flask app
    app.run(host=API_HOST, port=API_PORT, debug=API_DEBUG)

def stop_api():
    """Stop the Flask API server and worker thread"""
    if worker_thread:
        stop_worker()

if __name__ == '__main__':
    try:
        start_api()
    except KeyboardInterrupt:
        print("Shutting down API server...")
        stop_api()
