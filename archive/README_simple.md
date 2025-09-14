# Simple Page Visit Counter

A beginner-friendly FastAPI application that tracks page visits. Perfect for learning web APIs and Docker!

## What This App Does

- 📊 **Tracks page visits** - Records when someone visits a URL
- 🌐 **Provides statistics** - Shows total visits, unique visitors, and popular pages
- 🚀 **Easy to use** - Simple REST API with automatic documentation
- 🐳 **Docker ready** - Runs anywhere with Docker

## Quick Start

### Option 1: Run with Python

1. **Install dependencies:**
   ```bash
   pip install -r requirements_simple.txt
   ```

2. **Run the app:**
   ```bash
   python page_count_simple.py
   ```

3. **Open your browser:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs

### Option 2: Run with Docker

1. **Build and run:**
   ```bash
   docker-compose -f docker-compose.simple.yml up --build
   ```

2. **That's it!** The app is running at http://localhost:8000

## How to Use

### Record a Visit
```bash
# Using curl
curl -X POST "http://localhost:8000/visit" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://mywebsite.com/page1"}'

# Or just visit in browser
http://localhost:8000/?url=https://mywebsite.com/page1
```

### Get Statistics
```bash
curl http://localhost:8000/stats
```

Response:
```json
{
  "total_visits": 42,
  "unique_visitors": 15,
  "popular_pages": {
    "https://mywebsite.com/home": 20,
    "https://mywebsite.com/about": 15,
    "https://mywebsite.com/contact": 7
  },
  "recent_visits": [
    {
      "url": "https://mywebsite.com/home",
      "ip": "192.168.1.100",
      "timestamp": "2025-07-28 10:30:00"
    }
  ]
}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Record a visit (simple) |
| POST | `/visit` | Record a visit (JSON) |
| GET | `/stats` | Get visit statistics |
| GET | `/health` | Health check |
| GET | `/docs` | API documentation |

## Testing

Run the test script:
```bash
python test_simple.py
```

## File Structure

```
page_count/
├── page_count_simple.py      # Main application
├── requirements_simple.txt   # Python dependencies
├── Dockerfile.simple         # Docker configuration
├── docker-compose.simple.yml # Docker Compose
├── test_simple.py            # Test script
└── data/                     # Database files (created automatically)
```

## What You'll Learn

This project demonstrates:

- ✅ **FastAPI basics** - Creating REST APIs
- ✅ **Database operations** - SQLite with SQLAlchemy
- ✅ **Docker containerization** - Building and running containers
- ✅ **API documentation** - Automatic Swagger docs
- ✅ **HTTP methods** - GET and POST requests
- ✅ **JSON handling** - Request/response data
- ✅ **Error handling** - Graceful error management

## Perfect for YouTube!

This simplified version is ideal for tutorials because:

- 🎯 **Under 150 lines** of code
- 📚 **Well commented** and easy to understand
- 🔧 **Real-world example** with practical use
- 🐳 **Docker deployment** shows modern practices
- 📊 **Visual results** with statistics and data

## Raspberry Pi Deployment

This app runs great on Raspberry Pi! The Docker setup automatically handles ARM architecture.

```bash
# On your Raspberry Pi
git clone <your-repo>
cd page_count
docker-compose -f docker-compose.simple.yml up -d
```

## Next Steps

Once you understand this simple version, you can explore:

- Rate limiting
- User authentication
- More complex analytics
- Frontend dashboard
- Production deployment

Happy coding! 🚀
