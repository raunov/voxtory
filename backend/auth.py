from fastapi import Security, HTTPException, Depends, status
from fastapi.security.api_key import APIKeyHeader
from starlette.requests import Request
import time
from typing import Dict, List, Optional

from config import API_TOKENS, RATE_LIMIT, RATE_LIMIT_WINDOW, logger

# API key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Store request counts for rate limiting
# Structure: {token: [(timestamp, count), ...]}
request_counts: Dict[str, List[tuple]] = {}


def get_api_key(
    api_key_header: Optional[str] = Security(API_KEY_HEADER),
) -> str:
    """Validate the API key from the header."""
    if api_key_header in API_TOKENS:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key or missing authentication",
    )


def check_rate_limit(request: Request, api_key: str = Depends(get_api_key)) -> str:
    """Rate limiting middleware function."""
    current_time = time.time()
    
    # Initialize if this is the first request for this token
    if api_key not in request_counts:
        request_counts[api_key] = []
    
    # Filter out old requests outside the window
    request_counts[api_key] = [
        (ts, count) for ts, count in request_counts[api_key] 
        if current_time - ts < RATE_LIMIT_WINDOW
    ]
    
    # Count requests in the current window
    total_requests = sum(count for _, count in request_counts[api_key])
    
    # Check if rate limit exceeded
    if total_requests >= RATE_LIMIT:
        logger.warning(f"Rate limit exceeded for API key: {api_key[:5]}...")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT} requests per {RATE_LIMIT_WINDOW} seconds.",
        )
    
    # Add current request to the count
    request_counts[api_key].append((current_time, 1))
    
    return api_key
