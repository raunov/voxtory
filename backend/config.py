import os
from dotenv import load_dotenv
import logging
import secrets

# Load environment variables
load_dotenv()

# Environment type
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CORS settings
DEFAULT_CORS = "http://localhost:8000,http://localhost:3000" if ENVIRONMENT == "development" else ""
CORS_ORIGINS = os.getenv("CORS_ORIGINS", DEFAULT_CORS)

# Service name for logs
SERVICE_NAME = os.getenv("SERVICE_NAME", "voxtory")

# API configurations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable is not set")
    raise ValueError("GEMINI_API_KEY environment variable is not set")

# Gemini API configuration
MODEL_NAME = 'gemini-2.0-flash-thinking-exp'
GEMINI_HOST = "generativelanguage.googleapis.com"
GEMINI_PATH = f"/v1alpha/models/{MODEL_NAME}:generateContent"

# Server settings
HOST = '0.0.0.0'
PORT = 8000

# Authentication
# Get predefined API tokens or generate a random one if not set
DEFAULT_API_TOKEN = os.getenv("API_TOKEN", secrets.token_urlsafe(32))
API_TOKENS = os.getenv("API_TOKENS", DEFAULT_API_TOKEN).split(",")

# Rate limiting
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "10"))  # Number of requests per minute
RATE_LIMIT_WINDOW = 60  # Window in seconds

# File size limits
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB file size limit
