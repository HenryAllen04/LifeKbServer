#!/usr/bin/env python3
# LifeKB RAG Search Test Script
# Purpose: Test and validate RAG search functionality

import json
import urllib.request
import urllib.error
import os
import sys
from datetime import datetime

def test_rag_endpoint(base_url, token):
    """Test the RAG search endpoint with various scenarios"""
    
    print("🧪 Testing LifeKB RAG Search API")
    print(f"Base URL: {base_url}")
    print(f"Using token: {token[:10]}..." if token else "No token provided")
    print("-" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Basic Conversational Query",
            "data": {
                "query": "How have I been feeling lately?",
                "mode": "conversational",
                "include_sources": True,
                "limit": 5
            }
        },
        {
            "name": "Summary Mode Query", 
            "data": {
                "query": "Summarize my week",
                "mode": "summary",
                "include_sources": True,
                "limit": 10
            }
        },
        {
            "name": "Analysis Mode Query",
            "data": {
                "query": "What patterns do you see in my productivity?",
                "mode": "analysis",
                "include_sources": False,
                "limit": 8
            }
        },
        {
            "name": "No Sources Query",
            "data": {
                "query": "Tell me about my goals",
                "mode": "conversational",
                "include_sources": False
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"Query: '{test_case['data']['query']}'")
        print(f"Mode: {test_case['data']['mode']}")
        
        try:
            result = make_rag_request(base_url, token, test_case['data'])
            results.append({"test": test_case['name'], "success": True, "result": result})
            
            # Display key results
            if result.get('success'):
                print(f"✅ Success!")
                print(f"   AI Response: {result['ai_response'][:100]}...")
                print(f"   Sources: {result.get('total_sources', 0)}")
                print(f"   Time: {result.get('processing_time_ms', 0)}ms")
            else:
                print(f"❌ API returned error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            results.append({"test": test_case['name'], "success": False, "error": str(e)})
            print(f"❌ Request failed: {str(e)}")
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary")
    print("="*50)
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    print(f"Tests passed: {success_count}/{total_count}")
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['test']}")
        if not result['success']:
            print(f"   Error: {result.get('error', 'Unknown')}")
    
    return results

def make_rag_request(base_url, token, data):
    """Make a RAG search request"""
    url = f"{base_url}/api/search_rag"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    request_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=request_data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            return response_data
            
    except urllib.error.HTTPError as e:
        error_text = e.read().decode('utf-8') if e.fp else str(e)
        try:
            error_data = json.loads(error_text)
            return error_data
        except:
            raise Exception(f"HTTP {e.code}: {error_text}")

def test_endpoint_info(base_url):
    """Test the GET endpoint for API information"""
    print("🔍 Testing API Information Endpoint")
    
    try:
        url = f"{base_url}/api/search_rag"
        req = urllib.request.Request(url, method='GET')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        print("✅ API Info retrieved successfully:")
        print(f"   API: {data.get('api', 'Unknown')}")
        print(f"   Version: {data.get('version', 'Unknown')}")
        print(f"   Status: {data.get('status', 'Unknown')}")
        print(f"   Modes: {', '.join(data.get('modes', []))}")
        print(f"   OpenAI Configured: {data.get('environment', {}).get('openai_configured', False)}")
        print(f"   Supabase Configured: {data.get('environment', {}).get('supabase_configured', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to get API info: {str(e)}")
        return False

def validate_environment():
    """Validate required environment variables"""
    print("🔧 Validating Environment")
    
    required_vars = [
        "OPENAI_API_KEY",
        "SUPABASE_URL", 
        "SUPABASE_SERVICE_KEY",
        "JWT_SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * 8}...{os.environ[var][-4:]}")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All required environment variables are set")
    return True

def main():
    """Main test function"""
    print("🚀 LifeKB RAG Search API Test Suite")
    print("=" * 50)
    
    # Get configuration from environment or command line
    base_url = os.environ.get("TEST_BASE_URL", "https://your-lifekb-app.vercel.app")
    token = os.environ.get("TEST_JWT_TOKEN")
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        token = sys.argv[2]
    
    if not token:
        print("❌ JWT token required for testing")
        print("Usage: python test_rag.py [base_url] [jwt_token]")
        print("Or set TEST_BASE_URL and TEST_JWT_TOKEN environment variables")
        return False
    
    # Validate environment
    env_valid = validate_environment()
    if not env_valid:
        print("⚠️  Environment validation failed, but continuing with tests...")
    
    print(f"\n📡 Testing endpoint: {base_url}")
    
    # Test API info endpoint
    info_success = test_endpoint_info(base_url)
    
    if not info_success:
        print("❌ API info test failed, endpoint may not be available")
        return False
    
    # Test RAG functionality
    test_results = test_rag_endpoint(base_url, token)
    
    # Final summary
    success_count = sum(1 for r in test_results if r['success'])
    total_tests = len(test_results) + 1  # +1 for info endpoint
    
    print(f"\n🎯 Overall Results: {success_count + (1 if info_success else 0)}/{total_tests} tests passed")
    
    if success_count == len(test_results) and info_success:
        print("🎉 All tests passed! RAG API is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 