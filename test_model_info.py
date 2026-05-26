#!/usr/bin/env python3
"""Test script to verify model_info is included in responses."""

import requests
import json
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

PROXY_URL = "http://localhost:8082"

def test_model_info_non_streaming():
    """Test that model_info is included in non-streaming responses."""
    print("Testing non-streaming response...")

    response = requests.post(
        f"{PROXY_URL}/v1/messages",
        headers={
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        },
        json={
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "Say hello"}
            ]
        }
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response received")
        print(f"  Model: {data.get('model')}")

        if 'model_info' in data:
            model_info = data['model_info']
            print(f"✓ model_info present:")
            print(f"  max_input_tokens: {model_info.get('max_input_tokens')}")
            print(f"  max_output_tokens: {model_info.get('max_output_tokens')}")
        else:
            print(f"✗ model_info NOT present in response")
            print(f"  Response keys: {list(data.keys())}")
    else:
        print(f"✗ Request failed: {response.status_code}")
        print(f"  {response.text}")

def test_model_info_streaming():
    """Test that model_info is included in streaming responses."""
    print("\nTesting streaming response...")

    response = requests.post(
        f"{PROXY_URL}/v1/messages",
        headers={
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        },
        json={
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "stream": True
        },
        stream=True
    )

    if response.status_code == 200:
        print(f"✓ Streaming response started")

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('event: message_start'):
                    # Next line should be the data
                    continue
                elif line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        if data.get('type') == 'message_start':
                            message = data.get('message', {})
                            if 'model_info' in message:
                                model_info = message['model_info']
                                print(f"✓ model_info present in message_start:")
                                print(f"  max_input_tokens: {model_info.get('max_input_tokens')}")
                                print(f"  max_output_tokens: {model_info.get('max_output_tokens')}")
                                break
                            else:
                                print(f"✗ model_info NOT present in message_start")
                                print(f"  Message keys: {list(message.keys())}")
                                break
                    except json.JSONDecodeError:
                        continue
    else:
        print(f"✗ Request failed: {response.status_code}")
        print(f"  {response.text}")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing model_info in proxy responses")
    print("=" * 60)

    try:
        test_model_info_non_streaming()
        test_model_info_streaming()
        print("\n" + "=" * 60)
        print("Tests completed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
