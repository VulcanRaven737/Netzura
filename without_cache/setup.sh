#!/bin/bash

# Colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Load Balancing System...${NC}"

# Create log directory if it doesn't exist
mkdir -p logs

# Function to check if a port is already in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Kill processes using our ports if they exist
kill_existing() {
    echo -e "${YELLOW}Checking for existing processes on our ports...${NC}"
    
    # Define ports to check
    PORTS=(8000 8081 8082 8083 8084)
    
    for PORT in "${PORTS[@]}"; do
        if check_port $PORT; then
            PID=$(lsof -t -i:$PORT)
            echo -e "Killing process on port $PORT (PID: $PID)"
            kill -9 $PID 2>/dev/null
            sleep 1
        fi
    done
}

# Function to start a backend server
start_backend() {
    local id=$1
    local port=$2
    echo -e "${BLUE}Starting Backend Server $id on port $port...${NC}"
    SERVER_ID=$id PORT=$port python backend_server.py > logs/backend_$id.log 2>&1 &
    echo $! > logs/backend_$id.pid
    sleep 1
}

# Function to run the load balancer
start_load_balancer() {
    echo -e "${BLUE}Starting Load Balancer on port 8000...${NC}"
    python load_balancer.py > logs/load_balancer.log 2>&1 &
    echo $! > logs/load_balancer.pid
    sleep 2
}

# Kill any existing processes
kill_existing

# Start backend servers
start_backend 1 8081
start_backend 2 8082
start_backend 3 8083
start_backend 4 8084

# Start load balancer
start_load_balancer

echo -e "${GREEN}All components started!${NC}"
echo -e "Load Balancer is running on: http://localhost:8000"
echo -e "Backend Server 1 is running on: http://localhost:8081"
echo -e "Backend Server 2 is running on: http://localhost:8082"
echo -e "Backend Server 3 is running on: http://localhost:8083"
echo -e "Backend Server 4 is running on: http://localhost:8084"
echo
echo -e "${YELLOW}Logs are available in the logs/ directory${NC}"
echo -e "To stop all components, run: ${YELLOW}./stop.sh${NC}"

# Create a stop script for convenience
cat > stop.sh << 'EOF'
#!/bin/bash
echo "Stopping all components..."

# Kill load balancer
if [ -f logs/load_balancer.pid ]; then
    PID=$(cat logs/load_balancer.pid)
    kill -9 $PID 2>/dev/null
    rm logs/load_balancer.pid
    echo "Load balancer stopped"
fi

# Kill all backend servers
for i in {1..4}; do
    if [ -f logs/backend_$i.pid ]; then
        PID=$(cat logs/backend_$i.pid)
        kill -9 $PID 2>/dev/null
        rm logs/backend_$i.pid
        echo "Backend server $i stopped"
    fi
done

echo "All components stopped successfully"
EOF

chmod +x stop.sh

# Create a script to start locust for load testing
cat > run_locust.sh << 'EOF'
#!/bin/bash
echo "Starting Locust load testing tool..."
echo "Web interface will be available at: http://localhost:8089"
locust -f locust_test.py --host=http://localhost:8000
EOF

chmod +x run_locust.sh

echo -e "\n${GREEN}Created additional scripts:${NC}"
echo -e "- ${YELLOW}./stop.sh${NC}       - Stops all components"
echo -e "- ${YELLOW}./run_locust.sh${NC} - Starts Locust load testing tool"