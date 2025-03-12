import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# Determine if we're running in production
IS_PRODUCTION = os.environ.get('RENDER', False)

# Database settings
if IS_PRODUCTION:
    # PostgreSQL connection string for Render
    # Format: postgres://username:password@host:port/database_name
    DATABASE_URL = os.environ.get('DATABASE_URL')
    DB_TYPE = 'postgresql'
else:
    # SQLite for local development
    DB_PATH = os.path.join(BASE_DIR, "jobs.db")
    DB_TYPE = 'sqlite'

# API settings
API_HOST = os.environ.get('HOST', '0.0.0.0')
API_PORT = int(os.environ.get('PORT', 5000))
API_DEBUG = not IS_PRODUCTION

# Worker settings
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL', 5))  # seconds between job checks
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))      # webhook retry attempts
RETRY_DELAY = int(os.environ.get('RETRY_DELAY', 60))     # seconds between retry attempts

# Temp directory for uploaded files
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
