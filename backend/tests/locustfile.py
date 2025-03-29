from locust import HttpUser, task, between
import json
from datetime import datetime, timedelta

class FormiqUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and get access token"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword"
            }
        )
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @task(1)
    def get_user_profile(self):
        """Get user profile"""
        self.client.get("/api/v1/users/me", headers=self.headers)

    @task(2)
    def get_workouts(self):
        """Get user workouts"""
        self.client.get("/api/v1/workouts", headers=self.headers)

    @task(3)
    def get_workout_plans(self):
        """Get workout plans"""
        self.client.get("/api/v1/workout-plans", headers=self.headers)

    @task(4)
    def create_workout(self):
        """Create a new workout"""
        workout_data = {
            "name": f"Load Test Workout {datetime.now().timestamp()}",
            "description": "Load test workout",
            "duration": 45,
            "difficulty": "intermediate"
        }
        self.client.post(
            "/api/v1/workouts",
            headers=self.headers,
            json=workout_data
        )

    @task(5)
    def create_workout_plan(self):
        """Create a new workout plan"""
        plan_data = {
            "name": f"Load Test Plan {datetime.now().timestamp()}",
            "description": "Load test plan",
            "duration_weeks": 4
        }
        self.client.post(
            "/api/v1/workout-plans",
            headers=self.headers,
            json=plan_data
        )

    @task(6)
    def analyze_workout(self):
        """Analyze workout video"""
        # Simulate video upload
        files = {
            "video": ("test_video.mp4", open("test_video.mp4", "rb"), "video/mp4")
        }
        self.client.post(
            "/api/v1/workouts/analyze",
            headers={"Authorization": f"Bearer {self.token}"},
            files=files
        )

    @task(7)
    def get_subscription_status(self):
        """Get subscription status"""
        self.client.get("/api/v1/subscriptions/status", headers=self.headers)

    @task(8)
    def update_user_profile(self):
        """Update user profile"""
        update_data = {
            "username": f"loadtest_{datetime.now().timestamp()}"
        }
        self.client.patch(
            "/api/v1/users/me",
            headers=self.headers,
            json=update_data
        )

    @task(9)
    def get_workout_statistics(self):
        """Get workout statistics"""
        self.client.get("/api/v1/workouts/statistics", headers=self.headers)

    @task(10)
    def search_workouts(self):
        """Search workouts"""
        self.client.get(
            "/api/v1/workouts/search?q=test",
            headers=self.headers
        )

class FormiqAdminUser(HttpUser):
    wait_time = between(2, 4)
    
    def on_start(self):
        """Login as admin and get access token"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "adminpassword"
            }
        )
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @task(1)
    def get_all_users(self):
        """Get all users"""
        self.client.get("/api/v1/admin/users", headers=self.headers)

    @task(2)
    def get_system_metrics(self):
        """Get system metrics"""
        self.client.get("/api/v1/admin/metrics", headers=self.headers)

    @task(3)
    def get_audit_logs(self):
        """Get audit logs"""
        self.client.get("/api/v1/admin/audit-logs", headers=self.headers)

    @task(4)
    def manage_subscriptions(self):
        """Manage user subscriptions"""
        subscription_data = {
            "user_id": 1,
            "tier": "PRO",
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
        self.client.post(
            "/api/v1/admin/subscriptions",
            headers=self.headers,
            json=subscription_data
        ) 