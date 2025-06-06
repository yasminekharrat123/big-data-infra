
 ## Setup
 ```bash
 npm install
 npm run build
 npm start
 ```

 ## Development
 ```bash
 npm run dev
 ```

 ## Docker
 ```bash
 docker build -t express-app .
 docker run -p 3000:3000 express-app
 ```

 ## Endpoints
 - `GET /`: Random greetings to test if the app is working.
 - `GET /cpu?n=<number>`: CPU-intensive Fibonacci calculation (default n=40).
 - `GET /error`: Randomly throws different errors (~50% chance), including:
   - 500 Internal Server Error
   - 401 Unauthorized
   - 403 Forbidden
   - 404 Not Found
   - 400 Bad Request
 - `GET /memory-leak`: Simulates a memory leak by accumulating data.

 ## Logs
 - Morgan logs HTTP requests as a single JSON-stringified object including:
   - `method`: HTTP method
   - `url`: Request URL
   - `status`: HTTP status code
   - `contentLength`: Response content length
   - `params`: Query and body parameters
   - `response`: Response status and body
   - `error`: Error message (if any)
 - Examples of the log:
   ```
   {"method":"GET","url":"/cpu?n=4","status":304,"contentLength":"0","params":{"query":{"n":"4"}},"response":{"status":304,"body":{"message":"Fibonacci(4) = 3"}},"error":"No error"}
   {"method":"GET","url":"/error","status":400,"contentLength":"49","params":{"query":{}},"response":{"status":400,"body":{"error":"Bad Request: Invalid input parameters"}},"error":"Bad Request: Invalid input parameters"}
   ```

## Load Testing with Locust
 - Install Locust:
   ```bash
   pip install locust
   ```
 - Run Locust from the `locust/` directory:
   ```bash
   cd locust
   locust -f locustfile.py --host=http://localhost:3000 --users=50 --spawn-rate=5 --run-time=1m --headless
  ```
  - `--host=http://localhost:3000`: Sets the target host for the load test.
  - `--users=50`: number of simulated concurrent users.
  - `--spawn-rate=5`: Spawns 5 users per second until the total number of users is reached.
  - `--run-time=1m`: run the test for run-time minutes.
  - `--headless`: Runs Locust in headless mode (without a web UI).
   ```