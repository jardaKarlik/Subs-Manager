#!/usr/bin/env python3
"""
Test script for the Subscription Manager API
Tests all endpoints and functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['message']}")
            print(f"   Available endpoints: {', '.join(data['endpoints'])}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_add_test_data():
    """Test adding test data"""
    print("\n📊 Adding test data...")
    try:
        response = requests.post(f"{BASE_URL}/api/add-test-data")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Test data added: {data['message']}")
            return True
        else:
            print(f"❌ Failed to add test data: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Add test data error: {e}")
        return False

def test_get_subscriptions():
    """Test getting all subscriptions"""
    print("\n📋 Getting all subscriptions...")
    try:
        response = requests.get(f"{BASE_URL}/api/subscriptions")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved {len(data)} subscriptions:")
            for sub in data:
                print(f"   - {sub['service_name']}: ${sub['cost']}/{sub['billing_cycle']} ({sub['source']})")
            return True
        else:
            print(f"❌ Failed to get subscriptions: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get subscriptions error: {e}")
        return False

def test_get_summary():
    """Test getting subscription summary"""
    print("\n📈 Getting subscription summary...")
    try:
        response = requests.get(f"{BASE_URL}/api/summary")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Summary retrieved:")
            print(f"   - Total subscriptions: {data['total_subscriptions']}")
            print(f"   - Monthly cost: ${data['estimated_monthly_cost']}")
            print(f"   - Yearly cost: ${data['estimated_yearly_cost']}")
            return True
        else:
            print(f"❌ Failed to get summary: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get summary error: {e}")
        return False

def test_add_manual_subscription():
    """Test adding a manual subscription"""
    print("\n➕ Adding manual subscription...")
    try:
        new_sub = {
            "service_name": "Test Service",
            "cost": 19.99,
            "currency": "USD",
            "billing_cycle": "monthly",
            "start_date": "2024-01-01",
            "notes": "Added via API test",
            "source": "API Test"
        }
        
        response = requests.post(f"{BASE_URL}/api/subscriptions", json=new_sub)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Manual subscription added:")
            print(f"   - ID: {data['id']}")
            print(f"   - Service: {data['service_name']}")
            print(f"   - Cost: ${data['cost']}/{data['billing_cycle']}")
            return True
        else:
            print(f"❌ Failed to add manual subscription: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Add manual subscription error: {e}")
        return False

def test_parse_emails():
    """Test email parsing functionality"""
    print("\n📧 Testing email parsing...")
    try:
        response = requests.post(f"{BASE_URL}/api/parse-emails")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Email parsing completed:")
            print(f"   - {data['message']}")
            if 'results' in data:
                results = data['results']
                print(f"   - Processed: {results['processed']} emails")
                print(f"   - New subscriptions: {results['new_subscriptions']}")
                print(f"   - Skipped: {results['skipped']}")
                
                # Show details by source
                for source, details in results.get('sources', {}).items():
                    if details['new_subscriptions'] > 0:
                        print(f"   - {source}: {details['new_subscriptions']} new subscriptions")
                        for detail in details.get('details', []):
                            print(f"     * {detail['service']} - ${detail['cost']}")
            return True
        else:
            print(f"❌ Failed to parse emails: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Parse emails error: {e}")
        return False

def main():
    """Run all API tests"""
    print("🚀 Starting Subscription Manager API Tests")
    print("=" * 50)
    
    # Wait a moment for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    tests = [
        test_health,
        test_add_test_data,
        test_get_subscriptions,
        test_get_summary,
        test_add_manual_subscription,
        test_parse_emails,
        test_get_subscriptions,  # Check again after parsing
        test_get_summary,       # Check summary after all operations
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The Subscription Manager API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("\n💡 You can now:")
    print("   - Open http://localhost:8000/docs to see the API documentation")
    print("   - Test the frontend by opening the HTML file")
    print("   - Use the API endpoints in your applications")

if __name__ == "__main__":
    main()