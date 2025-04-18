import time
import json
import hashlib
import logging
from flask import Flask, request, Response, g
import requests
import redis
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('load_balancer')

app = Flask(__name__)

# Redis connection
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.ping()  # Test connection
    logger.info("Redis connection successful")
except Exception as e:
    logger.warning(f"Could not connect to Redis: {str(e)}. Continuing without caching")
    redis_client = None

CACHE_EXPIRY = 30  # 5 minutes cache expiry

# Backend server pool
BACKEND_SERVERS = [
    "http://localhost:8081",
    "http://localhost:8082", 
    "http://localhost:8083",
    "http://localhost:8084"
]

# Health check status
HEALTH_STATUS = {server: True for server in BACKEND_SERVERS}

# Create a class to hold the counter that persists between requests
class ServerCounter:
    def __init__(self):
        self.index = 0
        self.lock = threading.Lock()
    
    def get_next_index(self, num_servers):
        with self.lock:
            current = self.index
            self.index = (self.index + 1) % max(num_servers, 1)
            return current

# Initialize the counter
server_counter = ServerCounter()

def get_cache_key(request):
    """Generate a cache key based on request path and query parameters"""
    key = f"{request.path}:{request.query_string.decode('utf-8')}"
    return hashlib.md5(key.encode()).hexdigest()

def check_cache(request):
    """Check if response is in cache"""
    if request.method != 'GET' or redis_client is None:
        return None
    
    try:
        cache_key = get_cache_key(request)
        cached_response = redis_client.get(cache_key)
        
        if cached_response:
            logger.info(f"Cache hit for {request.path}")
            return json.loads(cached_response)
    except Exception as e:
        logger.error(f"Cache error: {str(e)}")
    
    return None

def update_cache(request, response):
    """Store response in cache"""
    if request.method != 'GET' or redis_client is None:
        return
    
    try:
        cache_key = get_cache_key(request)
        
        # Only cache successful responses
        if 200 <= response.status_code < 300:
            # Store response data and headers
            cache_data = {
                'status_code': response.status_code,
                'content': response.text,
                'headers': dict(response.headers)
            }
            redis_client.setex(cache_key, CACHE_EXPIRY, json.dumps(cache_data))
            logger.info(f"Cached response for {request.path}")
    except Exception as e:
        logger.error(f"Cache update error: {str(e)}")

def get_healthy_servers():
    """Return list of healthy backend servers"""
    healthy = [server for server in BACKEND_SERVERS if HEALTH_STATUS[server]]
    # If no servers are healthy, try all servers as a fallback
    if not healthy:
        logger.warning("No healthy servers found! Using all servers as fallback.")
        return BACKEND_SERVERS
    return healthy

def select_server_round_robin():
    """Select a backend server using round-robin algorithm"""
    servers = get_healthy_servers()
    
    if not servers:
        return None
    
    # Get the next index using our thread-safe counter
    idx = server_counter.get_next_index(len(servers))
    server = servers[idx]
    
    logger.info(f"Round robin selected server: {server} (index: {idx})")
    return server

def health_check():
    """Check health of all backend servers"""
    for server in BACKEND_SERVERS:
        try:
            response = requests.get(f"{server}/health", timeout=2)
            was_healthy = HEALTH_STATUS[server]
            HEALTH_STATUS[server] = response.status_code == 200
            
            # Log changes in health status
            if was_healthy != HEALTH_STATUS[server]:
                logger.warning(f"Health status change: {server} is now {'UP' if HEALTH_STATUS[server] else 'DOWN'}")
            else:
                logger.info(f"Health check: {server} is {'UP' if HEALTH_STATUS[server] else 'DOWN'}")
                
        except requests.RequestException as e:
            was_healthy = HEALTH_STATUS[server]
            HEALTH_STATUS[server] = False
            if was_healthy:
                logger.error(f"Health check failed for {server}: {str(e)}")

@app.route('/debug')
def debug_info():
    """Return debug information about the load balancer"""
    return {
        'current_index': server_counter.index,
        'healthy_servers': get_healthy_servers(),
        'all_servers': BACKEND_SERVERS,
        'health_status': HEALTH_STATUS
    }

@app.route('/lb-stats')
def stats():
    """Return load balancer statistics"""
    return {
        'algorithm': 'round_robin',
        'servers': {
            server: {
                'healthy': HEALTH_STATUS[server],
            } for server in BACKEND_SERVERS
        },
        'current_index': server_counter.index
    }

@app.route('/lb-health')
def lb_health():
    """Run health check and return results"""
    health_check()
    return {server: HEALTH_STATUS[server] for server in BACKEND_SERVERS}

@app.route('/reset-counter')
def reset_counter():
    """Reset the round-robin counter - useful for testing"""
    with server_counter.lock:
        server_counter.index = 0
    return {"message": "Counter reset to 0", "current_index": server_counter.index}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    """Main proxy function that forwards requests to backend servers"""
    # First, check cache for GET requests
    cached_response = check_cache(request)
    if cached_response:
        return Response(
            cached_response['content'],
            status=cached_response['status_code'],
            headers=cached_response['headers']
        )
    
    # Select a backend server using round robin
    server = select_server_round_robin()
    if not server:
        return {"error": "No backend servers available"}, 503
    
    # Forward the request to the selected backend server
    target_url = f"{server}/{path}"
    
    # Prepare headers to be forwarded
    headers = {key: value for key, value in request.headers if key != 'Host'}
    headers['X-Forwarded-For'] = request.remote_addr
    
    try:
        # Forward the request
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.args,
            data=request.get_data(),
            cookies=request.cookies,
            timeout=10
        )
        
        # Update cache if it's a GET request
        update_cache(request, response)
        
        # Prepare the response to the client
        proxy_response = Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )
        
        return proxy_response
        
    except requests.RequestException as e:
        logger.error(f"Request to {target_url} failed: {str(e)}")
        return {"error": f"Backend server error: {str(e)}"}, 502

# Background health check task
def start_health_check_thread():
    def run_health_checks():
        while True:
            try:
                health_check()
            except Exception as e:
                logger.error(f"Error in health check thread: {str(e)}")
            time.sleep(10)  # Check every 10 seconds
    
    thread = threading.Thread(target=run_health_checks)
    thread.daemon = True
    thread.start()
    logger.info("Health check thread started")

if __name__ == '__main__':
    # Start health check thread
    start_health_check_thread()
    
    # Make initial health check
    health_check()
    
    # Start the application
    logger.info("Starting load balancer on port 8000")
    app.run(host='0.0.0.0', port=8000, threaded=True)