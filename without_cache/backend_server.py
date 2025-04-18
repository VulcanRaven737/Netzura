from flask import Flask, request, jsonify
import time
import random
import os
import logging
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('backend_server')

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get server ID from environment or default to 1
SERVER_ID = os.environ.get('SERVER_ID', '1')
PORT = int(os.environ.get('PORT', 8081))

# Simulate server load (0-100%)
server_load = 0

@app.route('/health')
def health():
    """Health check endpoint"""
    # Return unhealthy if load is too high
    if server_load > 90:
        return '', 503
    return '', 200

@app.route('/')
def home():
    """Home route"""
    # Simulate some processing time based on server load
    processing_time = random.uniform(0.05, 0.2) * (1 + server_load / 100)
    time.sleep(processing_time)
    
    response = {
        "message": f"Response from Server {SERVER_ID}",
        "server_id": SERVER_ID,
        "load": server_load,
        "processing_time_ms": int(processing_time * 1000)
    }
    
    logger.info(f"Handled request for / on server {SERVER_ID}")
    return jsonify(response)

@app.route('/api/test')
def api_test():
    """Test API endpoint"""
    return jsonify({
        "status": "ok",
        "server_id": SERVER_ID,
        "message": "API test endpoint"
    })

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def catch_all(path):
    """Handle all other routes"""
    # Simulate varying response times
    processing_time = random.uniform(0.05, 0.3) * (1 + server_load / 100)
    time.sleep(processing_time)
    
    response = {
        "message": f"Handled {request.method} request for /{path} on Server {SERVER_ID}",
        "server_id": SERVER_ID,
        "path": path,
        "method": request.method,
        "load": server_load,
        "processing_time_ms": int(processing_time * 1000)
    }
    
    logger.info(f"Handled {request.method} request for /{path} on server {SERVER_ID}")
    return jsonify(response)

# Periodically adjust server load to simulate real conditions
def simulate_load_changes():
    import threading
    
    def adjust_load():
        global server_load
        while True:
            try:
                # Randomly adjust load up or down
                change = random.uniform(-10, 10)
                server_load = max(0, min(100, server_load + change))
                time.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Error in load simulation: {str(e)}")
    
    thread = threading.Thread(target=adjust_load)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    simulate_load_changes()
    logger.info(f"Starting backend server {SERVER_ID} on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)