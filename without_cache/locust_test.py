from locust import HttpUser, task, between
import logging
import json

class RoundRobinTester(HttpUser):
    wait_time = between(0.5, 2)  # Shorter wait times for more traffic
    
    @task(10)
    def get_home_page(self):
        """Simulate requests to the home page to verify round robin distribution"""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                # Try to parse JSON but don't fail the test if it's not JSON
                try:
                    data = response.json()
                    # Log which server responded if we can parse the JSON
                    if "server_id" in data:
                        logging.info(f"Request handled by server: {data['server_id']}")
                except Exception as e:
                    logging.info(f"Response is not JSON or couldn't be parsed: {str(e)}")
                    # Mark as success even if not JSON
                    pass
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(3)
    def api_test(self):
        """Test a simple API endpoint"""
        with self.client.get("/api/test", catch_response=True) as response:
            # Don't expect JSON, just check status code
            if response.status_code >= 400:
                response.failure(f"API request failed with status code {response.status_code}")
    
    @task(1)
    def check_lb_stats(self):
        """Check load balancer statistics"""
        with self.client.get("/lb-stats", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Could not get load balancer stats: {response.status_code}")