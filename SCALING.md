# RecruiterBook API Scaling

This document outlines the scaling optimizations implemented to make the RecruiterBook API more efficient at scale.

## Optimizations Implemented

### 1. Database Connection Pooling

Database connection pooling has been configured in `database.py` with these parameters:

- `pool_size=20`: Maximum number of connections in the pool
- `max_overflow=10`: Allows additional 10 connections beyond pool_size when needed
- `pool_timeout=30`: Timeout in seconds when waiting for a connection
- `pool_recycle=1800`: Recycles connections after 30 minutes to avoid stale connections
- `pool_pre_ping=True`: Verifies connection is valid before using

### 2. Redis Caching

The API now uses Redis for caching frequently accessed data:

- Read-heavy endpoints use caching with appropriate TTLs
- Write operations invalidate related cache entries
- Cache invalidation strategy is pattern-based for precision

## Setup for Development/Production

### Redis Setup

#### Local Development

1. Install Redis locally:
   ```
   # For macOS with Homebrew
   brew install redis
   
   # For Ubuntu/Debian
   sudo apt-get install redis-server
   ```

2. Start Redis:
   ```
   # macOS
   brew services start redis
   
   # Ubuntu/Debian
   sudo systemctl start redis-server
   ```

3. Set environment variable (optional, defaults to localhost):
   ```
   export REDIS_URL=redis://localhost:6379
   ```

#### Production Environment

1. Add Redis to your production environment (Railway, Render, etc.)

2. Set the `REDIS_URL` environment variable:
   ```
   REDIS_URL=redis://username:password@host:port
   ```

## Cache Configuration

### Cache TTLs (Time-To-Live)

- Company lists: 1 hour (3600s)
- Recruiter profiles: 30 minutes (1800s)
- Recruiter search: 10 minutes (600s)
- Review data: 30 minutes (1800s)
- Featured content: 2 hours (7200s)

### Cache Invalidation

Cache entries are automatically invalidated when:
- Creating or updating recruiters
- Posting, updating or deleting reviews
- Upvoting or downvoting reviews
- Deleting companies

## Further Scaling Recommendations

For future scaling needs, consider:

1. Read replicas for database
2. Implement database indexes for common query patterns
3. Content Delivery Network (CDN) for static assets
4. Move non-critical processing to background tasks
5. Database sharding for very large scale
6. Kubernetes for container orchestration and auto-scaling 