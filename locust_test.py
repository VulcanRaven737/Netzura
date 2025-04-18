from locust import HttpUser, task, between
import logging
import json
import random

class RoundRobinTester(HttpUser):
    wait_time = between(0.5, 2)  # Shorter wait times for more traffic

    @task(10)
    def get_home_page(self):
        """Simulate requests to the home page to verify round robin and cache variation"""
        rand_val = random.randint(1, 1000)  # This causes a cache miss for new values
        url = f"/?q={rand_val}"
        
        with self.client.get(url, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "server_id" in data:
                        logging.info(f"Request to {url} handled by server: {data['server_id']} (Load: {data.get('load', '?')}%)")
                except Exception as e:
                    logging.info(f"Response from {url} is not JSON or couldn't be parsed: {str(e)}")
            else:
                response.failure(f"Got status code {response.status_code} for {url}")

    @task(3)
    def api_test(self):
        """Test a simple API endpoint"""
        with self.client.get("/api/test", catch_response=True) as response:
            if response.status_code >= 400:
                response.failure(f"API request failed with status code {response.status_code}")

    @task(1)
    def check_lb_stats(self):
        """Check load balancer statistics"""
        with self.client.get("/lb-stats", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Could not get load balancer stats: {response.status_code}")

    @task(4)
    def time_lb(self):
        """Check load balancer time"""
        with self.client.get("/time", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Could not get load balancer time: {response.status_code}")
