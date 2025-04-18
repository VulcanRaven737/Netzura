#!/bin/bash

echo "Setting up load balancer environment..."

# Check if Redis is running
echo "Checking Redis server..."
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Starting Redis server..."
    redis-server --daemonize yes
    sleep 2
    # Verify Redis started correctly
    redis-cli ping > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to start Redis. Please install and start Redis manually."
        exit 1
    fi
fi
echo "Redis is running."

# Kill any existing instances
echo "Cleaning up any existing processes..."
pkill -f 'python backend_server.py' 2>/dev/null
pkill -f 'python load_balancer.py' 2>/dev/null
sleep 1

# Start backend servers
echo "Starting backend servers..."
SERVER_ID=1 PORT=8081 python backend_server.py > server1.log 2>&1 &
SERVER_ID=2 PORT=8082 python backend_server.py > server2.log 2>&1 &
SERVER_ID=3 PORT=8083 python backend_server.py > server3.log 2>&1 &
SERVER_ID=4 PORT=8084 python backend_server.py > server4.log 2>&1 &

# Wait for servers to initialize
echo "Waiting for backend servers to start..."
sleep 3

# Verify backend servers are running
echo "Verifying backend servers..."
for port in 8081 8082 8083 8084; do
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health)
    if [ "$response" == "200" ]; then
        echo "Server on port $port is running correctly."
    else
        echo "WARNING: Server on port $port is not responding properly. Check server$((port-8080)).log"
    fi
done

# Start load balancer
echo "Starting round robin load balancer on port 8000..."
python load_balancer.py > load_balancer.log 2>&1 &

# Wait for load balancer to initialize
echo "Waiting for load balancer to start..."
sleep 3

# Verify load balancer is running
echo "Verifying load balancer..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/lb-stats)
if [ "$response" == "200" ]; then
    echo "Load balancer is running correctly."
else
    echo "WARNING: Load balancer is not responding properly. Check load_balancer.log"
fi

echo -e "\nAll services have been started!"
echo "Load balancer is available at http://localhost:8000"
echo -e "\nTo run the Locust tests, execute:"
echo "locust -f locust_test.py --host=http://localhost:8000"
echo "Then open http://localhost:8089 in your browser"
echo -e "\nQuick test of the load balancer:"
for i in {1..4}; do
    echo "Request $i:"
    curl -s http://localhost:8000/
    echo -e "\n"
done

echo -e "\nTo view logs:"
echo "tail -f load_balancer.log     # Load balancer logs"
echo "tail -f server1.log           # Backend server 1 logs"
echo -e "\nPress Ctrl+C to stop all services when done"

# Wait for Ctrl+C
trap "pkill -f 'python load_balancer.py'; pkill -f 'python backend_server.py'; echo 'Services stopped.'" SIGINT
wait