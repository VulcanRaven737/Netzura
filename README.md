# Netzura

A simple load balancer simulator with Redis caching.  
Netzura efficiently distributes requests across multiple backend servers while leveraging Redis to cache responses and reduce backend load.

## Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/VulcanRaven737/Netzura.git
    cd Netzura
    ```

2. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Run Netzura**:

    ```bash
    bash setup.sh
    ```

## Configuration

You can configure backend servers, cache timeout settings, and load balancing strategies by editing the `load_balancer.py` file.

```python
BACKENDS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003"
]

CACHE_TIMEOUT = 60  # seconds
```

## Load Testing with Locust

Netzura includes a load testing script using Locust. You can simulate multiple users sending concurrent requests to the load balancer to measure performance and caching efficiency.

### To run Locust tests:

```bash
locust -f locust_test.py
```


