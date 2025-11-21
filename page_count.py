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

def get_db_connection():
    """Create a new database connection"""
    return psycopg2.connect(DATABASE_URL)

def init_database():
    """Initialize the PostgreSQL database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON visits(url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON visits(timestamp)")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Database initialized")

# Initialize database on startup
init_database()

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
    description="A simple API to track page visits using SQLite",
    version="1.0.0"
)

# Add CORS middleware to allow browser requests
# CORS means Cross-Origin Resource Sharing, which allows your API to be accessed from different domains.
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
    # Check if behind a proxy (like nginx)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Direct connection
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
        # Get visitor information
        url = visit_data.url
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Insert visit into database
        execute_query(
            "INSERT INTO visits (url, ip_address, user_agent, timestamp) VALUES (%s, %s, %s, %s)",
            (url, ip, user_agent, timestamp)
        )
        
        logger.info(f"Visit recorded: {url} from {ip}")
        
    
        # Count total visits for that URL
        total_row = execute_query(
            "SELECT COUNT(*) FROM visits WHERE url = %s", (url,), fetch="one"
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
        # Count total visits
        total_visits = execute_query("SELECT COUNT(*) FROM visits", fetch="one")[0]
        
        # Count unique visitors
        unique_visitors = execute_query("SELECT COUNT(DISTINCT ip_address) FROM visits", fetch="one")[0]
        
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
        
        # Format the response
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
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Insert visit into database
        execute_query(
            "INSERT INTO visits (url, ip_address, user_agent, timestamp) VALUES (%s, %s, %s, %s)",
            (url, ip, user_agent, timestamp)
        )
        
        # Count total visits for this URL
        total_row = execute_query(
            "SELECT COUNT(*) FROM visits WHERE url = %s", (url,), fetch="one"
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
from fastapi import Depends

@app.get("/all-visits")
def get_all_visits(
    start_date: Optional[str] = None,  # Format: YYYY-MM-DD
    end_date: Optional[str] = None,    # Format: YYYY-MM-DD
    since: Optional[str] = None,       # Format: YYYY-MM-DD HH:MM:SS or ISO
    range: Optional[str] = None,       # Format: YYYY-MM-DD,YYYY-MM-DD
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    format: Optional[str] = None,      # 'jsonl' for JSON Lines output
    response: Response = None
):
    """Get all visits, with optional date range, range, and incremental sync support. Supports JSONL output."""
    try:
        query = "SELECT url, ip_address, user_agent, timestamp FROM visits"
        conditions = []
        params = []

        # Range filtering (takes precedence)
        if range:
            try:
                start, end = [x.strip() for x in range.split(",")[:2]]
                # Always treat end as exclusive
                from datetime import datetime
                if len(start) == 10:
                    start += " 00:00:00"
                if len(end) == 10:
                    end = end + " 00:00:00"
                # If end is a full datetime, do not adjust, but always use < end (exclusive)
                conditions.append("timestamp >= %s")
                params.append(start)
                conditions.append("timestamp < %s")
                params.append(end)
            except Exception as e:
                logger.error(f"Invalid range parameter: {range} - {e}")
        else:
            # Date range filtering
            if start_date:
                conditions.append("date(timestamp) >= date(%s)")
                params.append(start_date)
            if end_date:
                conditions.append("date(timestamp) <= date(%s)")
                params.append(end_date)
            # Since timestamp filtering
            if since:
                conditions.append("timestamp > %s")
                params.append(since)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        if offset:
            query += " OFFSET ?"
            params.append(offset)

        # Debug: log the final query and params
        logger.info(f"/all-visits SQL: {query}")
        logger.info(f"/all-visits params: {params}")


        visits = execute_query(query, tuple(params), fetch="all")

        # Debug: log the raw and normalized timestamps for each visit
        visit_dicts = []
        for url, ip, user_agent, timestamp in (visits or []):
            norm_ts = timestamp
            try:
                dt = date_parser.parse(timestamp)
                norm_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logger.warning(f"Could not parse timestamp '{timestamp}': {e}")
            logger.info(f"Visit: url={url}, raw_ts={timestamp}, norm_ts={norm_ts}")
            visit_dicts.append({
                "url": url,
                "ip": ip,
                "user_agent": user_agent,
                "timestamp": norm_ts
            })

        if format == "jsonl":
            # Output as JSON Lines, one object per line, no summary
            content = "\n".join(json.dumps(v, ensure_ascii=False) for v in visit_dicts)
            return Response(content=content, media_type="application/jsonl")
        elif format == "csv":
            # Output as CSV
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
            # Default: JSON object with summary
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
