#!/usr/bin/env python3
"""
Complete Authentication Flow Test Script

This script tests the entire authentication flow including:
1. User registration
2. Login with onboarding check
3. Onboarding completion
4. Login after onboarding
5. Password reset functionality
6. Social auth endpoints

Run this after setting up the database and starting the backend server.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test user data
TEST_USER = {
    "email": "test.auth@formiq.com",
    "password": "TestPassword123!",
    "confirm_password": "TestPassword123!",
    "full_name": "Test Auth User"
}

class AuthFlowTester:
    def __init__(self):
        self.session = requests.Session()
        self.user_id = None
        self.access_token = None
        self.refresh_token = None
        
    def print_step(self, step: str):
        print(f"\n{'='*60}")
        print(f"STEP: {step}")
        print(f"{'='*60}")
        
    def print_result(self, success: bool, message: str, data: Any = None):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {message}")
        if data:
            print(f"Data: {json.dumps(data, indent=2)}")
    
    def test_registration(self) -> bool:
        """Test user registration"""
        self.print_step("User Registration")
        
        try:
            response = self.session.post(
                f"{API_BASE}/auth/register",
                json=TEST_USER
            )
            
            if response.status_code == 201:
                data = response.json()
                self.user_id = data.get("user", {}).get("id")
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                
                # Check that user has NOT completed onboarding
                user_data = data.get("user", {})
                has_completed_onboarding = user_data.get("has_completed_onboarding", True)
                
                if has_completed_onboarding:
                    self.print_result(False, "New user should not have completed onboarding")
                    return False
                
                self.print_result(True, f"User registered successfully", {
                    "user_id": self.user_id,
                    "has_completed_onboarding": has_completed_onboarding
                })
                return True
            else:
                self.print_result(False, f"Registration failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Registration error: {str(e)}")
            return False
    
    def test_login_before_onboarding(self) -> bool:
        """Test login before completing onboarding"""
        self.print_step("Login Before Onboarding")
        
        try:
            response = self.session.post(
                f"{API_BASE}/auth/login",
                data={
                    "username": TEST_USER["email"],
                    "password": TEST_USER["password"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                user_data = data.get("user", {})
                has_completed_onboarding = user_data.get("has_completed_onboarding", True)
                
                if has_completed_onboarding:
                    self.print_result(False, "User should not have completed onboarding yet")
                    return False
                
                self.print_result(True, "Login successful, user needs onboarding", {
                    "has_completed_onboarding": has_completed_onboarding
                })
                return True
            else:
                self.print_result(False, f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Login error: {str(e)}")
            return False
    
    def test_complete_onboarding(self) -> bool:
        """Test completing onboarding"""
        self.print_step("Complete Onboarding")
        
        if not self.access_token:
            self.print_result(False, "No access token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.post(
                f"{API_BASE}/auth/complete-onboarding",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                user_data = data.get("user", {})
                has_completed_onboarding = user_data.get("has_completed_onboarding", False)
                onboarding_completed_at = user_data.get("onboarding_completed_at")
                
                if not has_completed_onboarding:
                    self.print_result(False, "Onboarding should be marked as completed")
                    return False
                
                if not onboarding_completed_at:
                    self.print_result(False, "Onboarding completion timestamp should be set")
                    return False
                
                self.print_result(True, "Onboarding completed successfully", {
                    "has_completed_onboarding": has_completed_onboarding,
                    "onboarding_completed_at": onboarding_completed_at
                })
                return True
            else:
                self.print_result(False, f"Complete onboarding failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Complete onboarding error: {str(e)}")
            return False
    
    def test_login_after_onboarding(self) -> bool:
        """Test login after completing onboarding"""
        self.print_step("Login After Onboarding")
        
        try:
            response = self.session.post(
                f"{API_BASE}/auth/login",
                data={
                    "username": TEST_USER["email"],
                    "password": TEST_USER["password"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                user_data = data.get("user", {})
                has_completed_onboarding = user_data.get("has_completed_onboarding", False)
                
                if not has_completed_onboarding:
                    self.print_result(False, "User should have completed onboarding")
                    return False
                
                self.print_result(True, "Login successful, onboarding completed", {
                    "has_completed_onboarding": has_completed_onboarding
                })
                return True
            else:
                self.print_result(False, f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Login error: {str(e)}")
            return False
    
    def test_password_reset_request(self) -> bool:
        """Test password reset request"""
        self.print_step("Password Reset Request")
        
        try:
            response = self.session.post(
                f"{API_BASE}/auth/reset-password/request",
                json={"email": TEST_USER["email"]}
            )
            
            if response.status_code == 202:
                self.print_result(True, "Password reset request sent successfully")
                return True
            else:
                self.print_result(False, f"Password reset request failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Password reset request error: {str(e)}")
            return False
    
    def test_email_verification_request(self) -> bool:
        """Test email verification request"""
        self.print_step("Email Verification Request")
        
        try:
            response = self.session.post(
                f"{API_BASE}/auth/verify-email/request",
                json={"email": TEST_USER["email"]}
            )
            
            if response.status_code == 202:
                self.print_result(True, "Email verification request sent successfully")
                return True
            else:
                self.print_result(False, f"Email verification request failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Email verification request error: {str(e)}")
            return False
    
    def test_social_auth_endpoints(self) -> bool:
        """Test social auth endpoints (Google and Apple)"""
        self.print_step("Social Auth Endpoints")
        
        # Test Google OAuth endpoint
        try:
            response = self.session.post(
                f"{API_BASE}/auth/social/google",
                json={"token": "fake_google_token"}
            )
            
            # We expect this to fail with 400 (invalid token), not 500 or 404
            if response.status_code == 400:
                self.print_result(True, "Google OAuth endpoint exists and validates tokens")
                google_success = True
            else:
                self.print_result(False, f"Google OAuth endpoint issue: {response.status_code}")
                google_success = False
                
        except Exception as e:
            self.print_result(False, f"Google OAuth endpoint error: {str(e)}")
            google_success = False
        
        # Test Apple OAuth endpoint
        try:
            response = self.session.post(
                f"{API_BASE}/auth/social/apple",
                json={"token": "fake_apple_token"}
            )
            
            # We expect this to fail with 400 (invalid token), not 500 or 404
            if response.status_code == 400:
                self.print_result(True, "Apple OAuth endpoint exists and validates tokens")
                apple_success = True
            else:
                self.print_result(False, f"Apple OAuth endpoint issue: {response.status_code}")
                apple_success = False
                
        except Exception as e:
            self.print_result(False, f"Apple OAuth endpoint error: {str(e)}")
            apple_success = False
        
        return google_success and apple_success
    
    def test_token_validation(self) -> bool:
        """Test token validation endpoint"""
        self.print_step("Token Validation")
        
        if not self.access_token:
            self.print_result(False, "No access token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.post(
                f"{API_BASE}/auth/test-token",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                user_data = data.get("user", {})
                
                self.print_result(True, "Token validation successful", {
                    "user_id": user_data.get("id"),
                    "email": user_data.get("email")
                })
                return True
            else:
                self.print_result(False, f"Token validation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.print_result(False, f"Token validation error: {str(e)}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up test user"""
        self.print_step("Cleanup Test User")
        
        # Note: In a real scenario, you'd want to delete the test user
        # For now, just log out
        try:
            if self.access_token:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = self.session.post(
                    f"{API_BASE}/auth/logout",
                    headers=headers
                )
                
                if response.status_code == 200:
                    self.print_result(True, "Logout successful")
                    return True
                else:
                    self.print_result(False, f"Logout failed: {response.status_code}")
                    return False
            else:
                self.print_result(True, "No token to logout")
                return True
                
        except Exception as e:
            self.print_result(False, f"Cleanup error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all authentication flow tests"""
        print("🚀 Starting Complete Authentication Flow Tests")
        print(f"Testing against: {BASE_URL}")
        
        tests = [
            ("Registration", self.test_registration),
            ("Login Before Onboarding", self.test_login_before_onboarding),
            ("Complete Onboarding", self.test_complete_onboarding),
            ("Login After Onboarding", self.test_login_after_onboarding),
            ("Password Reset Request", self.test_password_reset_request),
            ("Email Verification Request", self.test_email_verification_request),
            ("Social Auth Endpoints", self.test_social_auth_endpoints),
            ("Token Validation", self.test_token_validation),
            ("Cleanup", self.cleanup),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"❌ FAIL: {test_name} - Unexpected error: {str(e)}")
                results.append((test_name, False))
        
        # Summary
        print(f"\n{'='*60}")
        print("AUTHENTICATION FLOW TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All authentication flow tests PASSED!")
            return True
        else:
            print("⚠️  Some authentication flow tests FAILED!")
            return False

if __name__ == "__main__":
    print("Authentication Flow Test Script")
    print("Make sure the backend server is running on http://localhost:8000")
    print("Press Enter to continue or Ctrl+C to cancel...")
    input()
    
    tester = AuthFlowTester()
    success = tester.run_all_tests()
    
    exit(0 if success else 1)