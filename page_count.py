from fastapi import FastAPI, Request, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import os
from typing import Optional
import json
from dateutil import parser as date_parser
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import time


def normalize_url(url: str) -> str:
    """Strip domain to get a relative path matching historic page_views data."""
    for prefix in ("https://www.kevsrobots.com/", "http://www.kevsrobots.com/",
                    "https://kevsrobots.com/", "http://kevsrobots.com/"):
        if url.startswith(prefix):
            path = url[len(prefix):]
            return path if path else "index.html"
    return url

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env_file()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please check your .env file.")

def get_db_connection(max_retries=3, retry_delay=2):
    """Create a new database connection with retry logic"""
    for attempt in range(max_retries):
        try:
            return psycopg2.connect(DATABASE_URL)
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                raise

def init_database(max_retries=10, retry_delay=5):
    """Initialize the PostgreSQL database with retry logic for startup"""
    logger.info("Initializing database...")

    for attempt in range(max_retries):
        try:
            conn = get_db_connection(max_retries=1)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS page_views (
                    id SERIAL PRIMARY KEY,
                    url VARCHAR NOT NULL,
                    ip_address VARCHAR,
                    user_agent VARCHAR,
                    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_views_url ON page_views(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_views_viewed_at ON page_views(viewed_at)")

            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Database initialized successfully!")
            return

        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logger.warning(f"Database initialization attempt {attempt + 1}/{max_retries} failed: {e}")
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to initialize database after {max_retries} attempts.")
                raise

# Pydantic models for API requests/responses
class VisitRequest(BaseModel):
    url: str

class VisitResponse(BaseModel):
    url: str
    ip: str
    user_agent: str
    status: str
    timestamp: str

# Create FastAPI app
app = FastAPI(
    title="Simple Page Visit Counter",
    description="A simple API to track page visits using PostgreSQL",
    version="1.0.0"
)

# Startup event to initialize database with retry logic
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    init_database()

# Add CORS middleware to allow browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to get client IP
def get_client_ip(request: Request) -> str:
    """Get the client IP address from the request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# Helper function to execute database queries
def execute_query(query: str, params: tuple = (), fetch: str = None):
    """Execute a database query and return results"""
    conn = get_db_connection()
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
        cursor.close()
        conn.close()

# Main endpoint to record a visit
@app.post("/visit", response_model=VisitResponse)
def record_visit(visit_data: VisitRequest, request: Request):
    """Record a page visit"""
    try:
        url = normalize_url(visit_data.url)
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        execute_query(
            "INSERT INTO page_views (url, ip_address, user_agent, viewed_at) VALUES (%s, %s, %s, %s)",
            (url, ip, user_agent, timestamp)
        )

        logger.info(f"Visit recorded: {url} from {ip}")

        total_row = execute_query(
            "SELECT COUNT(*) FROM page_views WHERE url = %s", (url,), fetch="one"
        )
        total = total_row[0] if total_row else 0

        return {
            "url": url,
            "ip": ip,
            "user_agent": user_agent,
            "status": f"Visit #{total:,} recorded",
            "timestamp": timestamp
        }

    except Exception as e:
        logger.error(f"Error recording visit: {e}")
        raise

# Get visit statistics
@app.get("/stats")
def get_stats():
    """Get visit statistics"""
    try:
        total_visits = execute_query("SELECT COUNT(*) FROM page_views", fetch="one")[0]
        unique_visitors = execute_query("SELECT COUNT(DISTINCT ip_address) FROM page_views", fetch="one")[0]

        recent_visits = execute_query(
            "SELECT url, ip_address, viewed_at FROM page_views ORDER BY viewed_at DESC LIMIT 10",
            fetch="all"
        )

        url_counts = execute_query(
            "SELECT url, COUNT(*) as count FROM page_views GROUP BY url ORDER BY count DESC",
            fetch="all"
        )

        return {
            "total_visits": f"{total_visits:,}",
            "unique_visitors": f"{unique_visitors:,}",
            "popular_pages": {url: f"{count:,}" for url, count in (url_counts or [])},
            "recent_visits": [
                {
                    "url": url,
                    "ip": ip,
                    "timestamp": timestamp
                }
                for url, ip, timestamp in (recent_visits or [])
            ]
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise

# Simple GET endpoint for easy testing
@app.get("/")
def record_visit_simple(url: str = Query(..., description="The URL being visited"), request: Request = None):
    """Simple endpoint to record a visit via GET request"""
    try:
        url = normalize_url(url)
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        execute_query(
            "INSERT INTO page_views (url, ip_address, user_agent, viewed_at) VALUES (%s, %s, %s, %s)",
            (url, ip, user_agent, timestamp)
        )

        total_row = execute_query(
            "SELECT COUNT(*) FROM page_views WHERE url = %s", (url,), fetch="one"
        )
        total = total_row[0] if total_row else 0

        logger.info(f"Visit recorded: {url} from {ip}")

        return {
            "message": "Visit recorded!",
            "url": url,
            "ip": ip,
            "timestamp": timestamp,
            "visits": f"{total:,}"
        }

    except Exception as e:
        logger.error(f"Error recording visit: {e}")
        raise

# Health check endpoint
@app.get("/health")
def health_check():
    """Check if the API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "database": "connected"
    }

# Get all visits (useful for debugging)
@app.get("/all-visits")
def get_all_visits(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    since: Optional[str] = None,
    range: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    format: Optional[str] = None,
    response: Response = None
):
    """Get all visits, with optional date range filtering."""
    try:
        query = "SELECT url, ip_address, user_agent, viewed_at FROM page_views"
        conditions = []
        params = []

        if range:
            try:
                start, end = [x.strip() for x in range.split(",")[:2]]
                if len(start) == 10:
                    start += " 00:00:00"
                if len(end) == 10:
                    end = end + " 00:00:00"
                conditions.append("viewed_at >= %s")
                params.append(start)
                conditions.append("viewed_at < %s")
                params.append(end)
            except Exception as e:
                logger.error(f"Invalid range parameter: {range} - {e}")
        else:
            if start_date:
                conditions.append("date(viewed_at) >= date(%s)")
                params.append(start_date)
            if end_date:
                conditions.append("date(viewed_at) <= date(%s)")
                params.append(end_date)
            if since:
                conditions.append("viewed_at > %s")
                params.append(since)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY viewed_at DESC"
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        if offset:
            query += " OFFSET %s"
            params.append(offset)

        visits = execute_query(query, tuple(params), fetch="all")

        visit_dicts = []
        for url, ip, user_agent, timestamp in (visits or []):
            norm_ts = timestamp
            try:
                dt = date_parser.parse(str(timestamp))
                norm_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logger.warning(f"Could not parse timestamp '{timestamp}': {e}")
            visit_dicts.append({
                "url": url,
                "ip": ip,
                "user_agent": user_agent,
                "timestamp": norm_ts
            })

        if format == "jsonl":
            content = "\n".join(json.dumps(v, ensure_ascii=False) for v in visit_dicts)
            return Response(content=content, media_type="application/jsonl")
        elif format == "csv":
            import io
            import csv
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["url", "ip", "user_agent", "timestamp"])
            writer.writeheader()
            writer.writerows(visit_dicts)
            content = output.getvalue()
            output.close()
            return Response(content=content, media_type="text/csv")
        else:
            return {
                "visits": visit_dicts,
                "total_count": f"{len(visit_dicts):,}"
            }
    except Exception as e:
        logger.error(f"Error getting all visits: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
