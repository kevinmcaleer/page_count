from fastapi import FastAPI, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from pydantic import BaseModel
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "sqlite:///./visits.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# Database model
class Visit(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True)
    url = Column(String, index=True)
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create database tables
Base.metadata.create_all(bind=engine)

# Pydantic models for API
class VisitRequest(BaseModel):
    url: str

class VisitResponse(BaseModel):
    url: str
    ip: str
    user_agent: str
    status: str
    timestamp: datetime

# Create FastAPI app
app = FastAPI(
    title="Simple Page Visit Counter",
    description="A simple API to track page visits",
    version="1.0.0"
)

# Add CORS middleware to allow browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to get client IP
def get_client_ip(request: Request) -> str:
    # Check if behind a proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

# Main endpoint to record a visit
@app.post("/visit", response_model=VisitResponse)
def record_visit(
    visit_data: VisitRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Record a page visit"""
    try:
        # Get visitor information
        url = visit_data.url
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Create and save visit record
        visit = Visit(
            url=url,
            ip_address=ip,
            user_agent=user_agent
        )
        db.add(visit)
        db.commit()
        
        logger.info(f"Visit recorded: {url} from {ip}")
        
        return VisitResponse(
            url=url,
            ip=ip,
            user_agent=user_agent,
            status="recorded",
            timestamp=visit.timestamp
        )
    except Exception as e:
        logger.error(f"Error recording visit: {e}")
        db.rollback()
        raise

# Get visit statistics
@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get visit statistics"""
    try:
        # Count total visits
        total_visits = db.query(Visit).count()
        
        # Count unique visitors
        unique_visitors = db.query(Visit.ip_address).distinct().count()
        
        # Get recent visits
        recent_visits = (
            db.query(Visit.url, Visit.ip_address, Visit.timestamp)
            .order_by(Visit.timestamp.desc())
            .limit(10)
            .all()
        )
        
        # Count visits per URL
        url_counts = {}
        all_visits = db.query(Visit.url).all()
        for (url,) in all_visits:
            url_counts[url] = url_counts.get(url, 0) + 1
        
        return {
            "total_visits": total_visits,
            "unique_visitors": unique_visitors,
            "popular_pages": url_counts,
            "recent_visits": [
                {
                    "url": url,
                    "ip": ip,
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
                }
                for url, ip, timestamp in recent_visits
            ]
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise

# Simple GET endpoint for easy testing
@app.get("/")
def record_visit_simple(
    url: str = Query(..., description="The URL being visited"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Simple endpoint to record a visit via GET request"""
    try:
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        visit = Visit(url=url, ip_address=ip, user_agent=user_agent)
        db.add(visit)
        db.commit()
        
        logger.info(f"Visit recorded: {url} from {ip}")
        return {"message": "Visit recorded!", "url": url, "ip": ip}
    except Exception as e:
        logger.error(f"Error recording visit: {e}")
        db.rollback()
        raise

# Health check
@app.get("/health")
def health_check():
    """Check if the API is running"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
