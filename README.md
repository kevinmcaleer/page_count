# Page Visit Counter API

A FastAPI-based web service for tracking page visits with analytics and rate limiting.

## Features

- **Visit Tracking**: Record page visits with IP addresses and user agents
- **Rate Limiting**: Prevent abuse with configurable rate limiting
- **Analytics**: Detailed statistics including hourly breakdowns and user agent analysis
- **Bulk Operations**: Record multiple visits at once for better performance
- **Data Cleanup**: Remove old visit records automatically
- **RESTful API**: Clean REST endpoints with OpenAPI documentation

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
uvicorn page_count:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Core Endpoints

#### `POST /visit`
Record a single page visit.

**Request Body:**
```json
{
  "url": "https://example.com/page"
}
```

**Response:**
```json
{
  "url": "https://example.com/page",
  "ip": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "status": "recorded",
  "timestamp": "2025-07-28T10:30:00"
}
```

#### `GET /?url=<url>`
Legacy endpoint for recording visits via GET request.

**Parameters:**
- `url`: The URL being visited

#### `POST /bulk-visits`
Record multiple visits at once (max 100 per request).

**Request Body:**
```json
[
  {"url": "https://example.com/page1"},
  {"url": "https://example.com/page2"}
]
```

### Analytics Endpoints

#### `GET /summary?hours=24`
Get comprehensive analytics for all tracked URLs.

**Parameters:**
- `hours` (optional): Hours to look back for time-based analytics (default: 24)

**Response:**
```json
{
  "data": {
    "https://example.com": {
      "total_visits": 150,
      "unique_ips": 45,
      "by_hour": {
        "2025-07-28 10:00:00": 5,
        "2025-07-28 11:00:00": 12
      },
      "user_agents": {
        "Mozilla/5.0...": 30,
        "Chrome/91.0...": 25
      },
      "recent_visits": [
        {
          "ip": "192.168.1.1",
          "user_agent": "Mozilla/5.0...",
          "timestamp": "2025-07-28T11:30:00"
        }
      ]
    }
  },
  "total_entries": 150,
  "date_range": {
    "earliest": "2025-07-20T10:00:00",
    "latest": "2025-07-28T11:30:00"
  }
}
```

#### `GET /stats/{url:path}?hours=24`
Get detailed statistics for a specific URL.

**Parameters:**
- `url`: The URL to get statistics for (URL-encoded)
- `hours` (optional): Hours to look back (default: 24)


### Utility Endpoints

#### `GET /all-visits`
Retrieve all visits, with advanced filtering and export options.

**Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `since` (optional): Only visits after this timestamp (YYYY-MM-DD HH:MM:SS)
- `range` (optional): Date range, format `YYYY-MM-DD,YYYY-MM-DD` (start inclusive, end exclusive). Takes precedence over other date filters.
- `limit` (optional): Limit number of results
- `offset` (optional): Offset for pagination
- `format` (optional): If set to `jsonl`, output is JSON Lines (one record per line, no summary)

**Default JSON Output:**
```json
{
  "visits": [
    {
      "url": "https://example.com/page",
      "ip": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2025-07-28 10:30:00"
    }
    // ...
  ],
  "total_count": "123"
}
```

**JSONL Output Example:**
Request: `/all-visits?range=2025-09-01,2025-09-07&format=jsonl`

Response:
```jsonl
{"url": "https://example.com/page", "ip": "192.168.1.1", "user_agent": "Mozilla/5.0...", "timestamp": "2025-09-01 12:00:00"}
{"url": "https://example.com/page2", "ip": "192.168.1.2", "user_agent": "Mozilla/5.0...", "timestamp": "2025-09-02 13:00:00"}
// ...
```

**Notes:**
- When `format=jsonl` is used, each line is a single JSON object and there is no summary or wrapper object.
- When both `range` and other date filters are provided, `range` takes precedence.

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-28T11:30:00"
}
```

#### `DELETE /cleanup?days=30`
Remove visit records older than specified days.

**Parameters:**
- `days` (optional): Delete visits older than this many days (default: 30)

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Standard endpoints**: 10 requests per minute per IP/URL combination
- **Bulk endpoint**: 20 requests per minute per IP/URL combination
- **Window**: 60 seconds rolling window

When rate limited, the API returns HTTP 429 with the message "Too many requests, please try again later".

## Database

The application uses SQLite with the following optimizations:

- **Indexes**: Optimized queries with composite indexes on URL+timestamp and URL+IP
- **Connection pooling**: Efficient database connection management
- **Automatic cleanup**: Built-in endpoint for removing old data

## Development

### Running Tests

```bash
python test_api.py
```

### API Documentation

When running the server, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Configuration

Key configuration options in the code:

- `DATABASE_URL`: SQLite database location
- Rate limiting parameters in `rate_limit_check()`
- CORS settings in middleware configuration

## Production Deployment

For production deployment:

1. **Security**: Update CORS and TrustedHost middleware settings
2. **Database**: Consider PostgreSQL for better concurrent access
3. **Rate Limiting**: Implement Redis-based rate limiting for distributed deployments
4. **Monitoring**: Add health checks and monitoring endpoints
5. **Reverse Proxy**: Use nginx or similar for SSL termination and load balancing

## Example Usage

```python
import requests

# Record a visit
response = requests.post(
    "http://localhost:8000/visit",
    json={"url": "https://mysite.com/page1"}
)

# Get analytics
response = requests.get("http://localhost:8000/summary?hours=24")
analytics = response.json()

# Get specific URL stats
response = requests.get("http://localhost:8000/stats/https://mysite.com/page1")
stats = response.json()
```

## License

This project is open source and available under the MIT License.
