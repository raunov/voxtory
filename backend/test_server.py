import os
import json
import requests
from dotenv import load_dotenv
from config import API_TOKENS, logger

# Load environment variables
load_dotenv()

# Get API key from environment variable
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY environment variable is not set")
    exit(1)
else:
    print("API Key loaded successfully")

# Get API token for testing
api_token = API_TOKENS[0] if API_TOKENS else None
if not api_token:
    print("ERROR: No API tokens configured")
    exit(1)
else:
    print(f"Using API token: {api_token[:5]}...")

def test_api_status():
    """Test the API status endpoint"""
    print("\n=== Testing API Status Endpoint ===")
    
    try:
        # Make request to status endpoint
        response = requests.get(
            "http://localhost:8000/api/status",
            headers={"X-API-Key": api_token}
        )
        
        # Check response
        if response.status_code == 200:
            print(f"✓ Status endpoint returned {response.status_code}")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"✗ Status endpoint returned error {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error connecting to API: {str(e)}")
        return False

def test_api_token():
    """Test the API token validation"""
    print("\n=== Testing API Token Validation ===")
    
    try:
        # Make request with invalid token
        response = requests.get(
            "http://localhost:8000/api/status",
            headers={"X-API-Key": "invalid_token"}
        )
        
        # Check response (should be unauthorized)
        if response.status_code == 401:
            print("✓ API correctly rejected invalid token")
        else:
            print(f"✗ API did not reject invalid token, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Make request with valid token
        response = requests.get(
            "http://localhost:8000/api/status",
            headers={"X-API-Key": api_token}
        )
        
        # Check response
        if response.status_code == 200:
            print("✓ API correctly accepted valid token")
            return True
        else:
            print(f"✗ API rejected valid token, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing token validation: {str(e)}")
        return False

def show_usage_instructions():
    """Show usage instructions for the API"""
    print("\n=== API Usage Instructions ===")
    print("\nTo use the API, make requests to the following endpoints:")
    print("\n1. Status Check:")
    print("   GET http://localhost:8000/api/status")
    print("   Headers: X-API-Key: your_api_token")
    
    print("\n2. Analyze Audio:")
    print("   POST http://localhost:8000/api/analyze")
    print("   Headers: X-API-Key: your_api_token")
    print("   Body: form-data with 'audiofile' field containing the audio file")
    
    print("\nFor testing, you can use the web interface at:")
    print("   http://localhost:8000")
    
    # Show current token for convenience
    print("\nYour current API token is:")
    print(f"   {api_token}")

if __name__ == "__main__":
    print("=== Testing Audio Analysis API ===")
    
    # Check if server is running
    try:
        requests.get("http://localhost:8000/api/status", timeout=2)
    except requests.exceptions.ConnectionError:
        print("✗ API server is not running. Please start the server first with:")
        print("   backend\\run_server.bat")
        exit(1)
    
    # Run tests
    status_test = test_api_status()
    token_test = test_api_token()
    
    # Show summary
    print("\n=== Test Summary ===")
    print(f"Status Endpoint Test: {'✓ Passed' if status_test else '✗ Failed'}")
    print(f"Token Validation Test: {'✓ Passed' if token_test else '✗ Failed'}")
    
    if status_test and token_test:
        print("\n✓ All tests passed!")
        show_usage_instructions()
    else:
        print("\n✗ Some tests failed. Please check the server logs for details.")
