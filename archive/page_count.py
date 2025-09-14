from fastapi import FastAPI, Depends, Request, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    func,
    distinct,
    Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, HttpUrl, validator
import logging
import os
import re
from functools import lru_cache
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLite config
DATABASE_URL = "sqlite:///./visits.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# Database model
class Visit(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True)
    url = Column(String, index=True)
    ip_address = Column(String, index=True)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

# Create additional indexes for better query performance
Index('idx_url_timestamp', Visit.url, Visit.timestamp)
Index('idx_url_ip', Visit.url, Visit.ip_address)

# Create DB schema
Base.metadata.create_all(bind=engine)

# Request/Response models
class VisitRequest(BaseModel):
    url: HttpUrl

class VisitResponse(BaseModel):
    url: str
    ip: str
    user_agent: str
    status: str
    timestamp: datetime

class URLStats(BaseModel):
    total_visits: int
    unique_ips: int
    by_hour: Dict[str, int]
    user_agents: Dict[str, int]
    recent_visits: List[Dict[str, Any]]

class SummaryResponse(BaseModel):
    data: Dict[str, URLStats]
    total_entries: int
    date_range: Dict[str, Optional[str]]

# FastAPI app
app = FastAPI(
    title="Page Visit Counter",
    description="A simple API to track page visits with analytics",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add TrustedHost middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Adjust this to your needs
)

# Add TrustedHost middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Adjust this to your needs
)

# DB session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Rate limiting cache
visit_cache = {}

def rate_limit_check(ip: str, url: str, window_seconds: int = 60, max_requests: int = 10) -> bool:
    """Check if the request should be rate limited"""
    current_time = time.time()
    key = f"{ip}:{url}"
    
    if key not in visit_cache:
        visit_cache[key] = []
    
    # Remove old entries outside the window
    visit_cache[key] = [t for t in visit_cache[key] if current_time - t < window_seconds]
    
    # Check if we're over the limit
    if len(visit_cache[key]) >= max_requests:
        return True
    
    # Add current request
    visit_cache[key].append(current_time)
    return False

# Enhanced URL validation with more strict checks
def validate_url(url: str) -> bool:
    if not url or len(url) > 2048:  # Check URL length
        return False
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

# Enhanced IP extraction with IPv6 support
def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers with fallback"""
    # Check X-Forwarded-For header first
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        ip = forwarded.split(",")[0].strip()
        return ip
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct client host
    return request.client.host if request.client else "unknown"

# Record visit with URL, IP, and User-Agent
@app.post("/visit", response_model=VisitResponse)
def count_visit(
    visit_data: VisitRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        url = str(visit_data.url)
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Rate limiting check
        if rate_limit_check(ip, url):
            raise HTTPException(status_code=429, detail="Too many requests, please try again later")
        
        # Create new visit record
        visit = Visit(url=url, ip_address=ip, user_agent=user_agent)
        db.add(visit)
        db.commit()
        db.refresh(visit)
        
        logger.info(f"Visit recorded: {url} from {ip}")
        
        return VisitResponse(
            url=url,
            ip=ip,
            user_agent=user_agent,
            status="recorded",
            timestamp=visit.timestamp
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error recording visit: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to record visit")

# Legacy endpoint for backwards compatibility
@app.get("/")
def count_visit_legacy(
    url: str = Query(..., description="The URL being visited"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    try:
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="Invalid URL format")
            
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        visit = Visit(url=url, ip_address=ip, user_agent=user_agent)
        db.add(visit)
        db.commit()
        
        logger.info(f"Visit recorded (legacy): {url} from {ip}")
        return {"url": url, "ip": ip, "user_agent": user_agent, "status": "recorded"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error recording visit (legacy): {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to record visit")

# Enhanced summary endpoint with analytics
@app.get("/summary", response_model=SummaryResponse)
def summary(
    hours: int = Query(default=24, description="Hours to look back for analytics"),
    db: Session = Depends(get_db)
):
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Total visits per URL (all time)
        total_visits = (
            db.query(Visit.url, func.count().label("visits"))
            .group_by(Visit.url)
            .all()
        )

        # Unique IPs per URL (all time)
        unique_ips = (
            db.query(Visit.url, func.count(distinct(Visit.ip_address)).label("unique_ips"))
            .group_by(Visit.url)
            .all()
        )

        # Visits per hour (within time range)
        visits_by_hour = (
            db.query(
                Visit.url,
                func.strftime('%Y-%m-%d %H:00:00', Visit.timestamp).label("hour"),
                func.count().label("count")
            )
            .filter(Visit.timestamp >= start_time)
            .group_by(Visit.url, "hour")
            .all()
        )

        # User-Agent breakdown per URL (within time range)
        user_agents = (
            db.query(Visit.url, Visit.user_agent, func.count().label("count"))
            .filter(Visit.timestamp >= start_time)
            .group_by(Visit.url, Visit.user_agent)
            .all()
        )

        # Recent visits (last 10 per URL)
        recent_visits_query = (
            db.query(Visit)
            .filter(Visit.timestamp >= start_time)
            .order_by(Visit.timestamp.desc())
            .limit(100)
            .all()
        )

        # Build response
        summary_data = {}
        for url, count in total_visits:
            summary_data[url] = URLStats(
                total_visits=count,
                unique_ips=0,
                by_hour={},
                user_agents={},
                recent_visits=[]
            )

        for url, count in unique_ips:
            if url in summary_data:
                summary_data[url].unique_ips = count

        for url, hour, count in visits_by_hour:
            if url in summary_data:
                summary_data[url].by_hour[hour] = count

        for url, agent, count in user_agents:
            if url in summary_data:
                summary_data[url].user_agents[agent] = count

        # Group recent visits by URL
        url_recent_visits = {}
        for visit in recent_visits_query:
            if visit.url not in url_recent_visits:
                url_recent_visits[visit.url] = []
            if len(url_recent_visits[visit.url]) < 10:  # Limit to 10 recent visits per URL
                url_recent_visits[visit.url].append({
                    "ip": visit.ip_address,
                    "user_agent": visit.user_agent,
                    "timestamp": visit.timestamp.isoformat()
                })

        for url in summary_data:
            summary_data[url].recent_visits = url_recent_visits.get(url, [])

        # Get date range info
        earliest = db.query(func.min(Visit.timestamp)).scalar()
        latest = db.query(func.max(Visit.timestamp)).scalar()
        
        total_entries = db.query(func.count(Visit.id)).scalar()

        return SummaryResponse(
            data=summary_data,
            total_entries=total_entries,
            date_range={
                "earliest": earliest.isoformat() if earliest else None,
                "latest": latest.isoformat() if latest else None
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate summary")

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Statistics endpoint for a specific URL
@app.get("/stats/{url:path}")
def url_stats(
    url: str,
    hours: int = Query(default=24, description="Hours to look back"),
    db: Session = Depends(get_db)
):
    try:
        # Decode URL and validate
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get stats for specific URL
        total_visits = db.query(func.count(Visit.id)).filter(Visit.url == url).scalar()
        unique_ips = db.query(func.count(distinct(Visit.ip_address))).filter(Visit.url == url).scalar()
        
        recent_visits = (
            db.query(Visit.ip_address, Visit.user_agent, Visit.timestamp)
            .filter(Visit.url == url, Visit.timestamp >= start_time)
            .order_by(Visit.timestamp.desc())
            .limit(20)
            .all()
        )
        
        hourly_data = (
            db.query(
                func.strftime('%Y-%m-%d %H:00:00', Visit.timestamp).label("hour"),
                func.count().label("count")
            )
            .filter(Visit.url == url, Visit.timestamp >= start_time)
            .group_by("hour")
            .all()
        )
        
        return {
            "url": url,
            "total_visits": total_visits,
            "unique_ips": unique_ips,
            "hourly_visits": {hour: count for hour, count in hourly_data},
            "recent_visits": [
                {
                    "ip": ip,
                    "user_agent": ua,
                    "timestamp": ts.isoformat()
                }
                for ip, ua, ts in recent_visits
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting URL stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get URL statistics")

# Bulk visit recording endpoint
@app.post("/bulk-visits")
def bulk_visits(
    visits: List[VisitRequest],
    request: Request,
    db: Session = Depends(get_db)
):
    """Record multiple visits at once for better performance"""
    try:
        if len(visits) > 100:  # Limit bulk operations
            raise HTTPException(status_code=400, detail="Too many visits in bulk request (max 100)")
        
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        visit_objects = []
        for visit_data in visits:
            url = str(visit_data.url)
            
            # Rate limiting check for each URL
            if rate_limit_check(ip, url, window_seconds=60, max_requests=20):
                logger.warning(f"Rate limit exceeded for bulk visit: {url} from {ip}")
                continue
            
            visit = Visit(url=url, ip_address=ip, user_agent=user_agent)
            visit_objects.append(visit)
        
        # Bulk insert
        db.add_all(visit_objects)
        db.commit()
        
        logger.info(f"Bulk visits recorded: {len(visit_objects)} visits from {ip}")
        
        return {
            "status": "recorded",
            "visits_recorded": len(visit_objects),
            "visits_rejected": len(visits) - len(visit_objects),
            "ip": ip
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error recording bulk visits: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to record bulk visits")

# Delete old visits (cleanup endpoint)
@app.delete("/cleanup")
def cleanup_old_visits(
    days: int = Query(default=30, description="Delete visits older than this many days"),
    db: Session = Depends(get_db)
):
    """Delete visits older than specified days"""
    try:
        if days < 1:
            raise HTTPException(status_code=400, detail="Days must be at least 1")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = db.query(Visit).filter(Visit.timestamp < cutoff_date).delete()
        db.commit()
        
        logger.info(f"Cleanup completed: {deleted_count} visits deleted")
        
        return {
            "status": "completed",
            "deleted_visits": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup old visits")
