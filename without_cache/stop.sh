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
