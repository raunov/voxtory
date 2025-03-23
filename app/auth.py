from fastapi import Depends, HTTPException, Header
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED

# Define the API key header
API_KEY_HEADER = APIKeyHeader(name="X-Gemini-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """
    Verify the Gemini API key provided in the request header.
    This is a simple validation that only checks if a key is provided.
    
    Args:
        api_key: The API key from the request header
        
    Returns:
        The API key if valid
        
    Raises:
        HTTPException: If the API key is missing or empty
    """
    if not api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="A valid Gemini API key is required. Please provide a valid key in the X-Gemini-API-Key header.",
        )
    return api_key
