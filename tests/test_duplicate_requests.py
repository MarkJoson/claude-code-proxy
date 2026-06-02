#!/usr/bin/env python3
"""
Test script to check if the proxy sends duplicate requests to upstream.
"""
import requests
import json
import time
import sys

# Test endpoint
url = "http://localhost:8082/v1/messages"

# Simple test request
payload = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 100,
    "messages": [
        {
            "role": "user",
            "content": "Say 'hello' and nothing else."
        }
    ]
}

headers = {
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01"
}

def test_non_streaming():
    print("="*60)
    print("TEST 1: NON-STREAMING REQUEST")
    print("="*60)

    test_payload = payload.copy()
    test_payload["stream"] = False

    print(f"URL: {url}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    print("\nCheck the server logs for:")
    print("  🔴 MIDDLEWARE: Incoming request - should appear ONCE")
    print("  🔵 ENDPOINT ENTRY - should appear ONCE")
    print("  🟡 NON-STREAMING MODE - should appear ONCE")
    print("  🟢 UPSTREAM CALL START - should appear ONCE (or more if retrying)")
    print("  🟢 UPSTREAM CALL SUCCESS - should appear ONCE")
    print("\n")

    start = time.time()
    response = requests.post(url, json=test_payload, headers=headers)
    elapsed = time.time() - start

    print(f"Response status: {response.status_code}")
    print(f"Response time: {elapsed:.2f}s")
    if response.status_code == 200:
        print(f"Response body: {json.dumps(response.json(), indent=2)[:500]}...")
    else:
        print(f"Error: {response.text}")
    print("\n")

def test_streaming():
    print("="*60)
    print("TEST 2: STREAMING REQUEST")
    print("="*60)

    test_payload = payload.copy()
    test_payload["stream"] = True

    print(f"URL: {url}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    print("\nCheck the server logs for:")
    print("  🔴 MIDDLEWARE: Incoming request - should appear ONCE")
    print("  🔵 ENDPOINT ENTRY - should appear ONCE")
    print("  🟡 STREAMING MODE - should appear ONCE")
    print("  🟢 UPSTREAM STREAMING CALL START - should appear ONCE (or more if retrying)")
    print("  🟢 UPSTREAM STREAMING CALL SUCCESS - should appear ONCE")
    print("\n")

    start = time.time()
    response = requests.post(url, json=test_payload, headers=headers, stream=True)
    elapsed = time.time() - start

    print(f"Response status: {response.status_code}")
    print(f"Response time: {elapsed:.2f}s")
    print(f"Response headers: {dict(response.headers)}")

    if response.status_code == 200:
        print("\nStreaming response chunks:")
        chunk_count = 0
        for line in response.iter_lines():
            if line:
                chunk_count += 1
                decoded = line.decode('utf-8')
                if len(decoded) > 100:
                    print(f"  Chunk {chunk_count}: {decoded[:100]}...")
                else:
                    print(f"  Chunk {chunk_count}: {decoded}")
                if chunk_count >= 5:  # Only show first 5 chunks
                    print("  ...")
                    break
    else:
        print(f"Error: {response.text}")
    print("\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("DUPLICATE REQUEST TEST")
    print("="*60 + "\n")

    # Test non-streaming first
    test_non_streaming()

    time.sleep(2)  # Wait a bit between tests

    # Test streaming
    test_streaming()

    print("="*60)
    print("TESTS COMPLETE")
    print("="*60)
    print("\nIf you see duplicate logs (2x of each), there's a problem.")
    print("Each test should show logs only ONCE.")
