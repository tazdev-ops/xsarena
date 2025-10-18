#!/usr/bin/env python3
"""
Test script to validate XSArena bridge endpoints
"""
import json

import requests


def test_endpoints():
    print("🔍 Testing XSArena bridge endpoints...")

    # Test /health endpoint
    try:
        response = requests.get("http://127.0.0.1:5102/health", timeout=5)
        print(f"✅ /health endpoint: Status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("⚠️  /health endpoint: Server not running (expected)")
    except Exception as e:
        print(f"❌ /health endpoint error: {e}")

    # Test /v1/health endpoint
    try:
        response = requests.get("http://127.0.0.1:5102/v1/health", timeout=5)
        print(f"✅ /v1/health endpoint: Status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("⚠️  /v1/health endpoint: Server not running (expected)")
    except Exception as e:
        print(f"❌ /v1/health endpoint error: {e}")

    # Test /internal/config endpoint
    try:
        response = requests.get("http://127.0.0.1:5102/internal/config", timeout=5)
        print(f"✅ /internal/config endpoint: Status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("⚠️  /internal/config endpoint: Server not running (expected)")
    except Exception as e:
        print(f"❌ /internal/config endpoint error: {e}")


def test_with_port_env():
    print("\n🔍 Testing with PORT environment variable...")
    # This would be tested when the server is run with PORT=5102
    print("   When running: PORT=5102 python api_server.py")
    print("   Server should start on port 5102")
    print("   Base URL for XSArena: http://127.0.0.1:5102/v1")


if __name__ == "__main__":
    test_endpoints()
    test_with_port_env()
    print("\n📝 To test fully:")
    print(
        "   1. Start the server: PORT=5102 python src/xsarena/bridge_v2/api_server.py"
    )
    print("   2. Open lmarena.ai with userscript active")
    print("   3. Run these commands:")
    print("      curl http://127.0.0.1:5102/health")
    print("      curl http://127.0.0.1:5102/internal/config")
