# YouTube Video Script: Building a Simple Page Visit Counter API

## Video Title: "Build Your First API in 20 Minutes - Page Visit Counter with FastAPI & SQLite"

### Duration: ~18-22 minutes
### Target Audience: Beginner programmers, Python learners, API beginners

---

## INTRO (0:00 - 1:30)

**[SCENE: Clean desktop, VS Code open]**

**HOST:** Hey everyone! Welcome back to the channel. Today we're going to build something really cool - a complete page visit counter API from scratch. 

**[GRAPHICS: Show final result - API documentation, stats dashboard]**

By the end of this video, you'll have:
- A working REST API that tracks website visits
- A SQLite database to store the data
- Docker containerization for easy deployment
- And you can run this on a Raspberry Pi!

**[GRAPHICS: Code complexity chart showing "Minimal Dependencies"]**

The best part? We're only using 3 Python packages and about 180 lines of code. No complex frameworks, no heavy databases - just clean, simple Python that actually works.

**[SCENE: Show file structure]**

Before we start coding, make sure you have Python 3.8+ installed. I'll put all the code and commands in the description below.

Let's dive in!

---

## PART 1: PROJECT SETUP (1:30 - 3:00)

**HOST:** First, let's set up our project. I'm creating a new folder called `page_counter`.

**[SCREEN: Terminal]**
```bash
mkdir page_counter
cd page_counter
```

**HOST:** Now let's create our requirements file. We're keeping this super minimal - just 3 packages:

**[SCREEN: Create requirements_minimal.txt]**
```
fastapi==0.116.1
uvicorn==0.35.0
pydantic==2.11.7
```

**HOST:** Let me explain what each of these does:
- **FastAPI** - This creates our web API. It's modern, fast, and has amazing automatic documentation
- **Uvicorn** - This runs our web server
- **Pydantic** - This validates our data and creates nice JSON responses

**[SCREEN: Terminal]**
```bash
pip install -r requirements_minimal.txt
```

**HOST:** While that installs, let me show you what we're building...

**[GRAPHICS: API endpoint diagram showing GET/POST requests]**

---

## PART 2: IMPORTS AND BASIC SETUP (3:00 - 5:00)

**HOST:** Now let's create our main file. I'm calling it `page_count_minimal.py`.

**[SCREEN: VS Code, new file]**

**HOST:** Let's start with our imports. I'll explain each one as we go:

```python
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import logging
import os
```

**HOST:** Let me break this down:
- `FastAPI` creates our web application
- `Request` lets us access information about incoming requests
- `Query` helps us handle URL parameters
- `CORSMiddleware` allows web browsers to call our API
- `BaseModel` from Pydantic validates our data
- `datetime` for timestamps
- `sqlite3` - this is built into Python! No external database needed
- `logging` to track what's happening
- `os` for file operations

**[SCREEN: Type logging setup]**

```python
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

**HOST:** Logging is super important. It tells us what's happening in our app, especially when things go wrong.

---

## PART 3: DATABASE SETUP (5:00 - 8:00)

**HOST:** Now here's where it gets interesting. Instead of using a complex ORM like SQLAlchemy, we're going raw SQLite. This is much easier to understand.

```python
# Database setup
DATABASE_PATH = "./data/visits.db"

def init_database():
    """Initialize the SQLite database"""
    # Create data directory if it doesn't exist
    os.makedirs("./data", exist_ok=True)
```

**HOST:** Notice how we're putting the database in a `data` folder. This makes it easy to back up or move our data later.

**[SCREEN: Continue typing]**

```python
    # Connect and create table
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
```

**HOST:** Let me explain this SQL:
- `id` - Auto-incrementing primary key. SQLite handles this for us
- `url` - The webpage that was visited
- `ip_address` - Who visited it
- `user_agent` - What browser they used
- `timestamp` - When it happened

**[GRAPHICS: Table diagram showing columns]**

```python
    # Create index for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON visits(url)")
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# Initialize database on startup
init_database()
```

**HOST:** The index makes our queries faster when we have lots of data. And we call `init_database()` right away so our table is ready to use.

**[PAUSE]**

**HOST:** This is so much cleaner than complex ORM setups! You can see exactly what's happening in the database.

---

## PART 4: PYDANTIC MODELS (8:00 - 9:30)

**HOST:** Now let's define our data models. Pydantic makes this really elegant:

```python
# Pydantic models for API requests/responses
class VisitRequest(BaseModel):
    url: str

class VisitResponse(BaseModel):
    url: str
    ip: str
    user_agent: str
    status: str
    timestamp: str
```

**HOST:** These models do two things:
1. They validate incoming data - if someone sends bad data, Pydantic catches it
2. They document our API - FastAPI uses these to generate documentation automatically

**[GRAPHICS: Show JSON request/response examples]**

When someone sends:
```json
{"url": "https://mywebsite.com"}
```

We respond with:
```json
{
  "url": "https://mywebsite.com",
  "ip": "192.168.1.100", 
  "status": "recorded",
  "timestamp": "2025-07-28 10:30:00"
}
```

---

## PART 5: FASTAPI APP SETUP (9:30 - 11:00)

**HOST:** Now let's create our FastAPI application:

```python
# Create FastAPI app
app = FastAPI(
    title="Simple Page Visit Counter",
    description="A simple API to track page visits using SQLite",
    version="1.0.0"
)
```

**HOST:** This metadata shows up in the automatic documentation. Speaking of which...

```python
# Add CORS middleware to allow browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**HOST:** CORS stands for Cross-Origin Resource Sharing. Without this, web browsers would block requests to our API. In production, you'd restrict this to specific domains, but for development, we're allowing everything.

**[SCREEN: Show helper functions]**

```python
# Helper function to get client IP
def get_client_ip(request: Request) -> str:
    """Get the client IP address from the request"""
    # Check if behind a proxy (like nginx)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Direct connection
    return request.client.host if request.client else "unknown"
```

**HOST:** This function figures out who's making the request. If you're behind a proxy or load balancer, the real IP might be in the `X-Forwarded-For` header.

---

## PART 6: DATABASE HELPER FUNCTION (11:00 - 12:30)

**HOST:** Here's a really clean pattern for database operations:

```python
# Helper function to execute database queries
def execute_query(query: str, params: tuple = (), fetch: str = None):
    """Execute a database query and return results"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute(query, params)
        
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()
        else:
            result = None
        
        conn.commit()
        return result
    
    finally:
        conn.close()
```

**HOST:** This function handles all our database operations. The `finally` block ensures we always close the connection, even if something goes wrong. The `params` tuple prevents SQL injection attacks - never put user data directly in SQL strings!

**[GRAPHICS: Show SQL injection example and prevention]**

---

## PART 7: MAIN API ENDPOINTS (12:30 - 16:00)

**HOST:** Now for the fun part - our API endpoints! Let's start with recording visits:

```python
# Main endpoint to record a visit
@app.post("/visit", response_model=VisitResponse)
def record_visit(visit_data: VisitRequest, request: Request):
    """Record a page visit"""
    try:
        # Get visitor information
        url = visit_data.url
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

**HOST:** The `@app.post` decorator creates a POST endpoint. FastAPI automatically:
- Validates the JSON against our `VisitRequest` model
- Converts the response to match our `VisitResponse` model
- Generates API documentation

```python
        # Insert visit into database
        execute_query(
            "INSERT INTO visits (url, ip_address, user_agent, timestamp) VALUES (?, ?, ?, ?)",
            (url, ip, user_agent, timestamp)
        )
        
        logger.info(f"Visit recorded: {url} from {ip}")
        
        return VisitResponse(
            url=url,
            ip=ip,
            user_agent=user_agent,
            status="recorded",
            timestamp=timestamp
        )
```

**HOST:** See how clean this is? One SQL INSERT statement, some logging, and we return the response. The question marks prevent SQL injection.

**[SCREEN: Continue with stats endpoint]**

```python
# Get visit statistics
@app.get("/stats")
def get_stats():
    """Get visit statistics"""
    try:
        # Count total visits
        total_visits = execute_query("SELECT COUNT(*) FROM visits", fetch="one")[0]
        
        # Count unique visitors
        unique_visitors = execute_query("SELECT COUNT(DISTINCT ip_address) FROM visits", fetch="one")[0]
```

**HOST:** Here we're using SQL aggregation functions. `COUNT(*)` counts all rows, `COUNT(DISTINCT ip_address)` counts unique IP addresses.

```python
        # Get recent visits (last 10)
        recent_visits = execute_query(
            "SELECT url, ip_address, timestamp FROM visits ORDER BY timestamp DESC LIMIT 10",
            fetch="all"
        )
        
        # Get popular pages (count visits per URL)
        url_counts = execute_query(
            "SELECT url, COUNT(*) as count FROM visits GROUP BY url ORDER BY count DESC",
            fetch="all"
        )
```

**HOST:** `ORDER BY timestamp DESC LIMIT 10` gets the 10 most recent visits. `GROUP BY url` groups visits by URL so we can count them.

**[SCREEN: Show response formatting]**

```python
        # Format the response
        return {
            "total_visits": total_visits,
            "unique_visitors": unique_visitors,
            "popular_pages": {url: count for url, count in url_counts},
            "recent_visits": [
                {
                    "url": url,
                    "ip": ip,
                    "timestamp": timestamp
                }
                for url, ip, timestamp in recent_visits
            ]
        }
```

**HOST:** Python's list and dictionary comprehensions make this data formatting really clean.

---

## PART 8: ADDITIONAL ENDPOINTS (16:00 - 17:30)

**HOST:** Let's add a few more useful endpoints:

```python
# Simple GET endpoint for easy testing
@app.get("/")
def record_visit_simple(url: str = Query(..., description="The URL being visited"), request: Request = None):
    """Simple endpoint to record a visit via GET request"""
```

**HOST:** This lets you record visits just by visiting a URL in your browser. The `Query(...)` makes `url` a required parameter.

```python
# Health check endpoint
@app.get("/health")
def health_check():
    """Check if the API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "database": "connected"
    }
```

**HOST:** Health checks are essential for production deployments. Load balancers and monitoring tools use these to know if your app is working.

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**HOST:** This lets us run the script directly with `python page_count_minimal.py`.

---

## PART 9: TESTING OUR API (17:30 - 19:00)

**HOST:** Let's test this! 

**[SCREEN: Terminal]**
```bash
python page_count_minimal.py
```

**[SCREEN: Browser showing http://localhost:8000/docs]**

**HOST:** Look at this! FastAPI automatically generated complete API documentation. This is why I love FastAPI - you get professional docs for free.

**[SCREEN: Test endpoints in the docs]**

Let's test the POST endpoint... I'll send:
```json
{"url": "https://mywebsite.com/home"}
```

**[SCREEN: Show response]**

Perfect! Now let's check our stats:

**[SCREEN: Visit /stats endpoint]**

**HOST:** Amazing! We can see our visit was recorded. Let's add a few more visits...

**[SCREEN: Use browser to visit /?url=https://example.com/about]**

**HOST:** The simple GET endpoint works too! This is great for tracking visits from websites that can't make POST requests.

---

## PART 10: DOCKER CONTAINERIZATION (19:00 - 20:30)

**HOST:** Now let's containerize this with Docker. This makes deployment super easy.

**[SCREEN: Create Dockerfile.minimal]**

```dockerfile
# Use Python 3.11 slim image (works great on Raspberry Pi)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements_minimal.txt .
RUN pip install --no-cache-dir -r requirements_minimal.txt

# Copy application code
COPY page_count_minimal.py .

# Create directory for database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "page_count_minimal:app", "--host", "0.0.0.0", "--port", "8000"]
```

**HOST:** This Dockerfile:
- Starts with a lightweight Python image
- Installs our dependencies
- Copies our code
- Creates the data directory
- Runs our app

**[SCREEN: Create docker-compose.minimal.yml]**

```yaml
version: '3.8'

services:
  page-counter-minimal:
    build:
      context: .
      dockerfile: Dockerfile.minimal
    container_name: page-counter-minimal
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

**HOST:** Docker Compose makes this even easier. The volume mount ensures our database persists even if we restart the container.

**[SCREEN: Terminal]**
```bash
docker-compose -f docker-compose.minimal.yml up --build
```

**HOST:** And just like that, we have a containerized API!

---

## CLOSING & NEXT STEPS (20:30 - 22:00)

**HOST:** Let's recap what we built:

**[GRAPHICS: Feature checklist]**
✅ Complete REST API with FastAPI
✅ SQLite database with raw SQL
✅ Automatic API documentation
✅ Docker containerization
✅ Only 3 dependencies
✅ About 180 lines of code
✅ Production-ready patterns

**HOST:** This runs great on a Raspberry Pi, and you could easily extend it with:
- User authentication
- Rate limiting
- A web dashboard
- Real-time analytics
- Geographic tracking

**[SCREEN: Show final file structure]**

All the code is available in the description. If you found this helpful, please like and subscribe - it really helps the channel!

**HOST:** In the next video, we'll build a React frontend for this API and add real-time updates with WebSockets. 

What would you like to see next? Let me know in the comments!

**[SCREEN: Subscribe button animation]**

Thanks for watching, and happy coding!

---

## VIDEO DESCRIPTION BOX CONTENT:

```
🚀 Build a complete page visit counter API from scratch using FastAPI and SQLite!

📁 GitHub Repository: [LINK]

⏰ TIMESTAMPS:
00:00 - Introduction & What We're Building
01:30 - Project Setup & Dependencies  
03:00 - Imports & Basic Configuration
05:00 - Database Setup with Raw SQLite
08:00 - Pydantic Models for Data Validation
09:30 - FastAPI App & Middleware Setup
11:00 - Database Helper Functions
12:30 - Main API Endpoints (POST /visit)
14:30 - Statistics Endpoint (GET /stats)
16:00 - Additional Utility Endpoints
17:30 - Testing Our API
19:00 - Docker Containerization
20:30 - Recap & Next Steps

📦 REQUIREMENTS:
- Python 3.8+
- fastapi==0.116.1
- uvicorn==0.35.0
- pydantic==2.11.7

🐳 DOCKER COMMANDS:
docker-compose -f docker-compose.minimal.yml up --build

🔗 USEFUL LINKS:
- FastAPI Documentation: https://fastapi.tiangolo.com/
- SQLite Tutorial: https://www.sqlite.org/lang.html
- Docker Installation: https://docs.docker.com/get-docker/

💡 WHAT YOU'LL LEARN:
✅ REST API development with FastAPI
✅ Database operations with SQLite
✅ API documentation with Swagger
✅ Docker containerization
✅ Production deployment patterns
✅ Error handling and logging

🎯 PERFECT FOR:
- Python beginners
- API development learners
- Full-stack developers
- DevOps enthusiasts

#Python #FastAPI #API #SQLite #Docker #WebDevelopment #Programming #Tutorial
```

---

## ADDITIONAL NOTES FOR CREATOR:

### **Preparation Checklist:**
- [ ] Clean desktop/VS Code setup
- [ ] Test all code snippets beforehand
- [ ] Prepare graphics for SQL table structure
- [ ] Have browser bookmarks ready for testing
- [ ] Pre-install Docker if demonstrating
- [ ] Prepare final demo with multiple visits

### **Graphics Needed:**
1. API endpoint diagram (GET/POST flow)
2. Database table structure visualization
3. JSON request/response examples
4. Docker container architecture
5. File structure tree
6. Feature checklist for closing

### **Camera Angles:**
- Primary: Screen capture with code
- Secondary: Face cam for explanations
- Consider picture-in-picture for complex sections

### **Pacing Notes:**
- Slower during database setup (most complex part)
- Faster during repetitive endpoint creation
- Pause for questions during testing phase
- Enthusiastic energy for Docker demo

This script should create an engaging, educational video that takes beginners from zero to a working, containerized API!
