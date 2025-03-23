import requests
import json
import argparse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api(youtube_url, language="en", api_url="http://localhost:8000"):
    """
    Test the Video Insights API by analyzing a YouTube video
    
    Args:
        youtube_url (str): The URL of the YouTube video to analyze
        language (str): Language code for output (default: 'en')
        api_url (str): URL of the API (default: http://localhost:8000)
    """
    # Get Gemini API key from environment or user input
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = input("Enter your Gemini API key: ")
        if not api_key:
            print("Error: Gemini API key is required")
            return
    
    # Set up request
    url = f"{api_url}/analyze"
    headers = {
        "Content-Type": "application/json",
        "X-Gemini-API-Key": api_key
    }
    payload = {
        "youtube_url": youtube_url,
        "language": language
    }
    
    print(f"Testing API at {url}")
    print(f"Analyzing YouTube video: {youtube_url}")
    print(f"Language: {language}")
    
    try:
        # Send request to API
        response = requests.post(url, headers=headers, json=payload)
        
        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            print("\nAPI Response:")
            print(json.dumps(result, indent=2))
            print("\nTest completed successfully!")
        else:
            print(f"\nError: API returned status code {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the Video Insights API")
    parser.add_argument("--url", "-u", type=str, required=True, help="YouTube URL to analyze")
    parser.add_argument("--language", "-l", type=str, default="en", help="Language code (default: en)")
    parser.add_argument("--api", "-a", type=str, default="http://localhost:8000", 
                        help="API URL (default: http://localhost:8000)")
    
    args = parser.parse_args()
    
    test_api(args.url, args.language, args.api)
