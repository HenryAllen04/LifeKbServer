#!/usr/bin/env python3
"""
LifeKB Metadata Features Test Script
Purpose: Comprehensive testing of all metadata functionality including CRUD, filtering, search, and analytics
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

class LifeKBTester:
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.test_user_email = f"test_{int(time.time())}@example.com"
        self.test_entries = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages."""
        print(f"[{level}] {message}")
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{endpoint}"
        
        if headers is None:
            headers = {"Content-Type": "application/json"}
        
        if self.access_token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.text else {},
                "success": 200 <= response.status_code < 300
            }
        except Exception as e:
            return {
                "status_code": 0,
                "data": {"error": str(e)},
                "success": False
            }
    
    def test_health_check(self) -> bool:
        """Test API health check."""
        self.log("Testing health check...")
        result = self.make_request("GET", "/api/auth?health=true")
        
        if result["success"]:
            self.log("✅ Health check passed")
            return True
        else:
            self.log(f"❌ Health check failed: {result['data']}", "ERROR")
            return False
    
    def test_authentication(self) -> bool:
        """Test user signup and login."""
        self.log("Testing authentication...")
        
        # Signup
        signup_data = {
            "action": "signup",
            "email": self.test_user_email,
            "password": "testpass123"
        }
        
        result = self.make_request("POST", "/api/auth", signup_data)
        if not result["success"]:
            self.log(f"❌ Signup failed: {result['data']}", "ERROR")
            return False
        
        # Login
        login_data = {
            "action": "login",
            "email": self.test_user_email,
            "password": "testpass123"
        }
        
        result = self.make_request("POST", "/api/auth", login_data)
        if result["success"]:
            self.access_token = result["data"].get("access_token")
            self.log("✅ Authentication successful")
            return True
        else:
            self.log(f"❌ Login failed: {result['data']}", "ERROR")
            return False
    
    def test_entry_creation_with_metadata(self) -> bool:
        """Test creating journal entries with metadata."""
        self.log("Testing entry creation with metadata...")
        
        test_entries = [
            {
                "text": "Today was an amazing day at the beach. I felt so grateful for the beautiful weather and time with family.",
                "tags": ["gratitude", "family", "beach"],
                "category": "personal",
                "mood": 9,
                "location": "Santa Monica Beach",
                "weather": "sunny"
            },
            {
                "text": "Had a challenging presentation at work today. Learned a lot about public speaking and handling pressure.",
                "tags": ["work", "learning", "challenge", "growth"],
                "category": "work",
                "mood": 7,
                "location": "Office",
                "weather": "cloudy"
            },
            {
                "text": "Went for a morning run and did some meditation. Feeling centered and healthy.",
                "tags": ["health", "meditation", "exercise"],
                "category": "health",
                "mood": 8,
                "location": "Park",
                "weather": "cool"
            }
        ]
        
        for i, entry_data in enumerate(test_entries):
            result = self.make_request("POST", "/api/entries", entry_data)
            
            if result["success"]:
                entry_id = result["data"]["entry"]["id"]
                self.test_entries.append(entry_id)
                self.log(f"✅ Entry {i+1} created with metadata: {entry_id}")
            else:
                self.log(f"❌ Entry {i+1} creation failed: {result['data']}", "ERROR")
                return False
        
        return True
    
    def test_entry_filtering(self) -> bool:
        """Test filtering entries by metadata."""
        self.log("Testing entry filtering...")
        
        test_filters = [
            {"category": "personal", "expected_min": 1},
            {"min_mood": 8, "expected_min": 2},
            {"tags": ["gratitude"], "expected_min": 1},
        ]
        
        for filter_test in test_filters:
            query_params = []
            expected_min = filter_test.pop("expected_min")
            
            for key, value in filter_test.items():
                if isinstance(value, list):
                    for item in value:
                        query_params.append(f"{key}={item}")
                else:
                    query_params.append(f"{key}={value}")
            
            query_string = "&".join(query_params)
            endpoint = f"/api/entries?{query_string}"
            
            result = self.make_request("GET", endpoint)
            
            if result["success"]:
                total_count = result["data"].get("total_count", 0)
                if total_count >= expected_min:
                    self.log(f"✅ Filter test passed: {filter_test} returned {total_count} entries")
                else:
                    self.log(f"❌ Filter test failed: {filter_test} expected at least {expected_min}, got {total_count}", "ERROR")
                    return False
            else:
                self.log(f"❌ Filter test failed: {result['data']}", "ERROR")
                return False
        
        return True
    
    def test_semantic_search_with_filters(self) -> bool:
        """Test semantic search with metadata filtering."""
        self.log("Testing semantic search with metadata filtering...")
        
        search_data = {
            "query": "gratitude and family time",
            "limit": 5,
            "similarity_threshold": 0.1,
            "filters": {
                "tags": ["gratitude"],
                "min_mood": 7
            }
        }
        
        result = self.make_request("POST", "/api/search", search_data)
        
        if result["success"]:
            results_count = len(result["data"].get("results", []))
            search_time = result["data"].get("search_time_ms", 0)
            
            self.log(f"✅ Semantic search successful: {results_count} results in {search_time}ms")
            return True
        else:
            self.log(f"❌ Semantic search failed: {result['data']}", "ERROR")
            return False
    
    def test_metadata_analytics(self) -> bool:
        """Test metadata analytics endpoint."""
        self.log("Testing metadata analytics...")
        
        result = self.make_request("GET", "/api/metadata?days=30")
        
        if result["success"]:
            stats = result["data"].get("stats", {})
            basic_stats = stats.get("basic_stats", {})
            popular_tags = stats.get("popular_tags", [])
            insights = stats.get("insights", {})
            
            self.log(f"✅ Analytics successful:")
            self.log(f"   Total entries: {basic_stats.get('total_entries', 0)}")
            self.log(f"   Average mood: {basic_stats.get('average_mood', 'N/A')}")
            self.log(f"   Popular tags: {len(popular_tags)}")
            self.log(f"   Most active day: {insights.get('most_active_day', 'N/A')}")
            return True
        else:
            self.log(f"❌ Analytics failed: {result['data']}", "ERROR")
            return False
    
    def test_tag_suggestions(self) -> bool:
        """Test tag suggestions endpoint."""
        self.log("Testing tag suggestions...")
        
        suggestion_data = {
            "text": "Had a great workout at the gym today. Feeling strong and motivated to continue my fitness journey."
        }
        
        result = self.make_request("POST", "/api/metadata", suggestion_data)
        
        if result["success"]:
            suggestions = result["data"].get("suggested_tags", [])
            self.log(f"✅ Tag suggestions successful: {suggestions}")
            return True
        else:
            self.log(f"❌ Tag suggestions failed: {result['data']}", "ERROR")
            return False
    
    def test_entry_update_with_metadata(self) -> bool:
        """Test updating entries with metadata."""
        self.log("Testing entry updates with metadata...")
        
        if not self.test_entries:
            self.log("❌ No test entries available for update test", "ERROR")
            return False
        
        entry_id = self.test_entries[0]
        update_data = {
            "mood": 10,
            "tags": ["updated", "amazing", "grateful"]
        }
        
        result = self.make_request("PUT", f"/api/entries?id={entry_id}", update_data)
        
        if result["success"]:
            updated_entry = result["data"]["entry"]
            if updated_entry["mood"] == 10:
                self.log("✅ Entry update successful")
                return True
            else:
                self.log("❌ Entry update data mismatch", "ERROR")
                return False
        else:
            self.log(f"❌ Entry update failed: {result['data']}", "ERROR")
            return False
    
    def cleanup(self):
        """Clean up test data."""
        self.log("Cleaning up test data...")
        
        for entry_id in self.test_entries:
            result = self.make_request("DELETE", f"/api/entries?id={entry_id}")
            if result["success"]:
                self.log(f"✅ Deleted entry: {entry_id}")
            else:
                self.log(f"❌ Failed to delete entry: {entry_id}", "ERROR")
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        self.log("Starting LifeKB Metadata Features Test Suite")
        self.log("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Authentication", self.test_authentication),
            ("Entry Creation with Metadata", self.test_entry_creation_with_metadata),
            ("Entry Filtering", self.test_entry_filtering),
            ("Semantic Search with Filters", self.test_semantic_search_with_filters),
            ("Metadata Analytics", self.test_metadata_analytics),
            ("Tag Suggestions", self.test_tag_suggestions),
            ("Entry Updates with Metadata", self.test_entry_update_with_metadata),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running: {test_name} ---")
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"❌ {test_name} crashed: {str(e)}", "ERROR")
                failed += 1
            
            # Small delay between tests
            time.sleep(1)
        
        # Cleanup
        self.cleanup()
        
        # Results summary
        self.log("\n" + "=" * 50)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 50)
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")
        self.log(f"Total: {passed + failed}")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED! Metadata features are working correctly.")
            return True
        else:
            self.log(f"⚠️  {failed} tests failed. Please check the logs above.")
            return False

def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LifeKB metadata features")
    parser.add_argument("--url", default="http://localhost:3001", help="Base URL for the API")
    args = parser.parse_args()
    
    tester = LifeKBTester(args.url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 