from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
from typing import Dict, Any
import json
import random
import time
import logging
import statsd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# StatsD client for metrics
statsd_client = statsd.StatsClient('localhost', 8125)

class FormIQUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.headers = {}
        self.session_start = None
        self.failed_requests = 0
        self.max_failures = 3  # Circuit breaker threshold

    def on_start(self):
        """Setup user authentication and monitoring."""
        self.session_start = datetime.now()
        try:
            self._login()
            statsd_client.incr('user.login.success')
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            statsd_client.incr('user.login.failure')
            raise

    def _login(self):
        """Handle authentication with circuit breaker pattern."""
        for attempt in range(self.max_failures):
            try:
                response = self.client.post("/api/v1/auth/login", json={
                    "email": f"loadtest{self.user_id}@example.com",
                    "password": "testpassword123"
                })
                
                if response.status_code == 200:
                    self.token = response.json()["tokens"]["accessToken"]
                    self.headers = {"Authorization": f"Bearer {self.token}"}
                    return
                
                logger.warning(f"Login attempt {attempt + 1} failed")
                time.sleep(1)  # Backoff
            except Exception as e:
                logger.error(f"Login attempt {attempt + 1} error: {str(e)}")
                if attempt == self.max_failures - 1:
                    raise

    @task(3)
    def view_form_history(self):
        """View form check history."""
        self.client.get("/api/v1/form-analysis/history", headers=self.headers)

    @task(2)
    def submit_form_check(self):
        """Submit a new form check."""
        # Simulate video upload
        with open("tests/load/sample_video.mp4", "rb") as f:
            files = {"video": ("workout.mp4", f, "video/mp4")}
            self.client.post(
                "/api/v1/form-analysis/analyze",
                headers=self.headers,
                files=files
            )

    @task(4)
    def view_exercises(self):
        """Browse exercise library."""
        self.client.get("/api/v1/exercises", headers=self.headers)
        
        # View random exercise details
        exercise_id = random.randint(1, 100)
        self.client.get(f"/api/v1/exercises/{exercise_id}", headers=self.headers)

    @task(1)
    def update_profile(self):
        """Update user profile."""
        self.client.put(
            "/api/v1/profile",
            headers=self.headers,
            json={
                "name": f"Load Test User {self.user_id}",
                "preferences": {
                    "notifications": True,
                    "theme": "dark"
                }
            }
        )

    @task(2)
    def search_exercises(self):
        """Search exercises."""
        search_terms = ["squat", "deadlift", "bench press", "pullup"]
        term = random.choice(search_terms)
        self.client.get(
            f"/api/v1/exercises/search?query={term}",
            headers=self.headers
        )

    @task(1)
    def filter_exercises(self):
        """Filter exercises."""
        filters = {
            "type": random.choice(["strength", "cardio", "flexibility"]),
            "difficulty": random.choice(["beginner", "intermediate", "advanced"]),
            "equipment": random.choice(["bodyweight", "barbell", "dumbbell"]),
        }
        self.client.get(
            "/api/v1/exercises/filter",
            params=filters,
            headers=self.headers
        )

    @task(3)
    def test_form_analysis(self):
        """Test form analysis with performance monitoring."""
        try:
            with statsd_client.timer('form_analysis.duration'):
                # Test model confidence thresholds
                confidence_threshold = 0.7
                
                # Simulate video upload and analysis
                with open("tests/load/sample_video.mp4", "rb") as f:
                    files = {"video": ("workout.mp4", f, "video/mp4")}
                    
                    start_time = time.time()
                    response = self.client.post(
                        "/api/v1/form-analysis/analyze",
                        headers=self.headers,
                        files=files
                    )
                    duration = time.time() - start_time
                    
                    # Log performance metrics
                    statsd_client.timing('form_analysis.response_time', duration * 1000)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Validate model confidence
                        if result.get('confidence', 0) < confidence_threshold:
                            logger.warning(f"Low confidence detection: {result.get('confidence')}")
                            statsd_client.incr('model.low_confidence')
                        
                        # Monitor pose detection success
                        if not result.get('poses'):
                            logger.error("No poses detected")
                            statsd_client.incr('model.no_poses_detected')
                            return
                        
                        statsd_client.incr('form_analysis.success')
                    else:
                        statsd_client.incr('form_analysis.error')
                        logger.error(f"Form analysis failed: {response.text}")
                        
        except Exception as e:
            logger.error(f"Form analysis error: {str(e)}")
            statsd_client.incr('form_analysis.exception')
            self.failed_requests += 1
            
            if self.failed_requests >= self.max_failures:
                logger.critical("Circuit breaker triggered - too many failures")
                self.environment.runner.quit()

    @task(2)
    def test_concurrent_requests(self):
        """Test handling of concurrent form analysis requests."""
        try:
            # Simulate multiple concurrent requests
            futures = []
            with statsd_client.timer('concurrent_requests.duration'):
                for _ in range(3):  # Simulate 3 concurrent requests
                    with open("tests/load/sample_video.mp4", "rb") as f:
                        files = {"video": ("workout.mp4", f, "video/mp4")}
                        self.client.post(
                            "/api/v1/form-analysis/analyze",
                            headers=self.headers,
                            files=files,
                            catch_response=True
                        )
            
            statsd_client.incr('concurrent_requests.completed')
        except Exception as e:
            logger.error(f"Concurrent requests error: {str(e)}")
            statsd_client.incr('concurrent_requests.error')

class AdminUser(FormIQUser):
    weight = 1  # Lower weight for admin users

    def on_start(self):
        """Setup admin authentication."""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "admin@formiq.app",
            "password": "adminpassword123"
        })
        self.token = response.json()["tokens"]["accessToken"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(1)
    def view_metrics(self):
        """View application metrics."""
        self.client.get("/metrics", headers=self.headers)

    @task(2)
    def manage_users(self):
        """Manage user accounts."""
        self.client.get("/api/v1/admin/users", headers=self.headers)

class WebsocketUser(FormIQUser):
    """User for testing real-time features."""
    
    def on_start(self):
        super().on_start()
        self.ws = self.client.get("/api/v1/ws", headers=self.headers)

    @task
    def stream_form_analysis(self):
        """Stream form analysis data."""
        if hasattr(self, 'ws'):
            message = {
                "type": "form_analysis",
                "data": {
                    "timestamp": time.time(),
                    "keypoints": []  # Add sample keypoints here
                }
            }
            self.ws.send(json.dumps(message))

@events.quitting.add_listener
def _(environment, **kw):
    """Handle test completion and generate comprehensive report."""
    if isinstance(environment.runner, MasterRunner):
        # Generate detailed performance report
        logger.info("Generating test summary...")
        # Add additional reporting logic here

@events.request_failure.add_listener
def _(request_type, name, response_time, exception, **kwargs):
    """Handle and log request failures."""
    logger.error(f"Request failed: {name}, Error: {str(exception)}")
    statsd_client.incr(f'request.failure.{name.replace("/", ".")}') 