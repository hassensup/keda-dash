#!/usr/bin/env python3
"""
Backend API Testing for KEDA Dashboard
Tests all API endpoints with proper authentication
"""

import requests
import sys
import json
from datetime import datetime

class KEDADashboardTester:
    def __init__(self, base_url="https://keda-dashboard.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   {method} {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json() if response.content else {}
                    if response_data and isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                    elif response_data and isinstance(response_data, list):
                        print(f"   Response: {len(response_data)} items")
                except:
                    pass
            else:
                self.failed_tests.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text[:200]}")

            return success, response.json() if response.content and success else {}

        except Exception as e:
            self.failed_tests.append(f"{name}: Exception - {str(e)}")
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health(self):
        """Test health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        return success and response.get('status') == 'ok'

    def test_login(self, email, password):
        """Test login and get token"""
        success, response = self.run_test(
            "Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'token' in response:
            self.token = response['token']
            print(f"   Token received: {self.token[:20]}...")
            return True
        return False

    def test_login_invalid(self):
        """Test login with invalid credentials"""
        success, response = self.run_test(
            "Login Invalid Credentials",
            "POST",
            "auth/login",
            401,
            data={"email": "wrong@example.com", "password": "wrongpass"}
        )
        return success

    def test_auth_me(self):
        """Test get current user"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success and 'email' in response

    def test_scaled_objects_list(self):
        """Test list scaled objects"""
        success, response = self.run_test(
            "List ScaledObjects",
            "GET",
            "scaled-objects",
            200
        )
        if success:
            print(f"   Found {len(response)} ScaledObjects")
            if len(response) > 0:
                print(f"   First object: {response[0].get('name', 'Unknown')}")
        return success

    def test_scaled_objects_filters(self):
        """Test scaled objects with filters"""
        # Test namespace filter
        success1, response1 = self.run_test(
            "List ScaledObjects - Namespace Filter",
            "GET",
            "scaled-objects",
            200,
            params={"namespace": "production"}
        )
        
        # Test scaler type filter
        success2, response2 = self.run_test(
            "List ScaledObjects - Scaler Type Filter",
            "GET",
            "scaled-objects",
            200,
            params={"scaler_type": "cron"}
        )
        
        return success1 and success2

    def test_namespaces(self):
        """Test list namespaces"""
        success, response = self.run_test(
            "List Namespaces",
            "GET",
            "namespaces",
            200
        )
        if success:
            print(f"   Found namespaces: {response}")
        return success

    def test_scaler_types(self):
        """Test list scaler types"""
        success, response = self.run_test(
            "List Scaler Types",
            "GET",
            "scaler-types",
            200
        )
        if success:
            print(f"   Found scaler types: {response}")
        return success

    def test_cron_events_list(self):
        """Test list cron events"""
        success, response = self.run_test(
            "List Cron Events",
            "GET",
            "cron-events",
            200
        )
        if success:
            print(f"   Found {len(response)} cron events")
        return success

    def test_scaled_object_crud(self):
        """Test ScaledObject CRUD operations"""
        # Create
        test_so = {
            "name": f"test-scaler-{datetime.now().strftime('%H%M%S')}",
            "namespace": "test",
            "scaler_type": "cpu",
            "target_deployment": "test-app",
            "min_replicas": 1,
            "max_replicas": 5,
            "triggers": [{"type": "cpu", "metadata": {"type": "Utilization", "value": "70"}}]
        }
        
        success_create, created_so = self.run_test(
            "Create ScaledObject",
            "POST",
            "scaled-objects",
            200,
            data=test_so
        )
        
        if not success_create:
            return False
            
        so_id = created_so.get('id')
        if not so_id:
            print("❌ No ID returned from create")
            return False
            
        # Read
        success_read, read_so = self.run_test(
            "Get ScaledObject",
            "GET",
            f"scaled-objects/{so_id}",
            200
        )
        
        # Update
        update_data = {"max_replicas": 8, "status": "Paused"}
        success_update, updated_so = self.run_test(
            "Update ScaledObject",
            "PUT",
            f"scaled-objects/{so_id}",
            200,
            data=update_data
        )
        
        # Delete
        success_delete, _ = self.run_test(
            "Delete ScaledObject",
            "DELETE",
            f"scaled-objects/{so_id}",
            200
        )
        
        return success_create and success_read and success_update and success_delete

    def test_cron_event_crud(self):
        """Test CronEvent CRUD operations"""
        # First get a ScaledObject to associate with
        success, scaled_objects = self.run_test(
            "Get ScaledObjects for Cron Test",
            "GET",
            "scaled-objects",
            200
        )
        
        if not success or not scaled_objects:
            print("❌ No ScaledObjects available for cron event test")
            return False
            
        so_id = scaled_objects[0]['id']
        
        # Create cron event
        test_event = {
            "scaled_object_id": so_id,
            "name": f"test-event-{datetime.now().strftime('%H%M%S')}",
            "timezone_str": "UTC",
            "desired_replicas": 3,
            "event_date": "2024-12-31",
            "start_time": "09:00",
            "end_time": "17:00"
        }
        
        success_create, created_event = self.run_test(
            "Create Cron Event",
            "POST",
            "cron-events",
            200,
            data=test_event
        )
        
        if not success_create:
            return False
            
        event_id = created_event.get('id')
        if not event_id:
            print("❌ No ID returned from cron event create")
            return False
            
        # Update
        update_data = {"desired_replicas": 5, "start_time": "08:00"}
        success_update, _ = self.run_test(
            "Update Cron Event",
            "PUT",
            f"cron-events/{event_id}",
            200,
            data=update_data
        )
        
        # Delete
        success_delete, _ = self.run_test(
            "Delete Cron Event",
            "DELETE",
            f"cron-events/{event_id}",
            200
        )
        
        return success_create and success_update and success_delete

    def test_auth_logout(self):
        """Test logout"""
        success, response = self.run_test(
            "Logout",
            "POST",
            "auth/logout",
            200
        )
        return success

def main():
    print("🚀 Starting KEDA Dashboard Backend API Tests")
    print("=" * 60)
    
    # Setup
    tester = KEDADashboardTester()
    
    # Test health first
    if not tester.test_health():
        print("❌ Health check failed, stopping tests")
        return 1

    # Test authentication
    if not tester.test_login("admin@example.com", "admin123"):
        print("❌ Login failed, stopping tests")
        return 1

    # Test invalid login
    tester.test_login_invalid()

    # Test authenticated endpoints
    tester.test_auth_me()
    tester.test_scaled_objects_list()
    tester.test_scaled_objects_filters()
    tester.test_namespaces()
    tester.test_scaler_types()
    tester.test_cron_events_list()
    
    # Test CRUD operations
    tester.test_scaled_object_crud()
    tester.test_cron_event_crud()
    
    # Test logout
    tester.test_auth_logout()

    # Print results
    print("\n" + "=" * 60)
    print(f"📊 Tests completed: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.failed_tests:
        print("\n❌ Failed tests:")
        for failure in tester.failed_tests:
            print(f"   - {failure}")
    else:
        print("\n✅ All tests passed!")
    
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    print(f"📈 Success rate: {success_rate:.1f}%")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())