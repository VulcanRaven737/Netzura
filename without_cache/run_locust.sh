#!/bin/bash
echo "Starting Locust load testing tool..."
echo "Web interface will be available at: http://localhost:8089"
locust -f locust_test.py --host=http://localhost:8000
