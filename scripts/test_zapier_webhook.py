#!/usr/bin/env python3
"""Test script for Zapier webhook integration."""
import requests
import json
import argparse
from typing import Dict, Any

def send_test_data(url: str, api_key: str, exercise_type: str) -> Dict[str, Any]:
    """
    Send test data to FormIQ training API.
    
    Args:
        url: API endpoint URL
        api_key: API key for authentication
        exercise_type: Type of exercise to test
        
    Returns:
        API response as dictionary
    """
    # Create test payload
    payload = {
        "exercise_type": exercise_type,
        "source": "zapier_test",
        "expert_score": 0.9,
        "feedback": [
            "Test feedback item 1",
            "Test feedback item 2"
        ],
        "metadata": {
            "test_id": "12345",
            "test_source": "zapier_integration_test",
            "timestamp": "2023-01-01T12:00:00Z"
        },
        "video_url": f"https://example.com/test/{exercise_type}_example.mp4"
    }
    
    # Set up headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Send request
    print(f"Sending test data for {exercise_type} to {url}")
    response = requests.post(url, json=payload, headers=headers)
    
    # Process response
    status_code = response.status_code
    
    try:
        response_data = response.json()
    except json.JSONDecodeError:
        response_data = {"error": "Invalid JSON response"}
    
    print(f"Response code: {status_code}")
    print(f"Response body: {json.dumps(response_data, indent=2)}")
    
    return {
        "status_code": status_code,
        "response": response_data
    }

def main():
    """Run the main script function."""
    parser = argparse.ArgumentParser(description="Test FormIQ Zapier Webhook Integration")
    parser.add_argument("--url", required=True, help="API endpoint URL")
    parser.add_argument("--api-key", required=True, help="API key for authentication")
    parser.add_argument("--exercise", default="squat", help="Exercise type to test")
    
    args = parser.parse_args()
    
    result = send_test_data(args.url, args.api_key, args.exercise)
    
    # Check result
    if result["status_code"] in (200, 201):
        print("\n✅ Test successful! Zapier integration is working correctly.")
    else:
        print("\n❌ Test failed. Check the response for more details.")
    
if __name__ == "__main__":
    main() 