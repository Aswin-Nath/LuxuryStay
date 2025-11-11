# 🏢 Production Readiness Audit Report
**Hotel Booking System - FastAPI Backend**

**Report Date:** November 11, 2025  
**Audit Scope:** Infrastructure, Security, Performance, Observability, Database, Caching, Deployment, Code Quality, Resilience, and Operations

---

## Executive Summary

Your backend is **~60% production-ready**. Strong foundations exist (async FastAPI, connection pooling, JWT auth, hybrid DB). However, critical gaps in security, observability, resilience, and deployment infrastructure must be addressed before production deployment.

**Risk Level:** 🟠 **MODERATE** (multiple 🔴 critical issues)

---

## 🔴 CRITICAL ISSUES (Must Fix Before Production)

| # | Issue | Severity | Impact | Recommendation |
|---|-------|----------|--------|-----------------|
| **1** | CORS Allow-All (`*`) | 🔴 CRITICAL | XSS/CSRF vectors, credential leakage | Restrict origins: `allow_origins=["https://yourdomain.com"]` |
| **2** | No HTTPS/TLS Enforcement | 🔴 CRITICAL | Man-in-the-middle attacks, credential sniffing | Add HTTPS redirect middleware, require TLS in production |
| **3** | No Rate Limiting | 🔴 CRITICAL | Brute force, DoS attacks on auth endpoints | Add `slowapi` or `limiter` middleware (e.g., 5 login attempts/min) |
| **4** | No Request/Response Validation Logging | 🔴 CRITICAL | Unable to audit sensitive operations (payments, refunds) | Log all write operations with sanitized data |
| **5** | Bare `print()` Statements | 🔴 CRITICAL | Logs lost in production (no structured logging) | Replace with `loguru` + JSON formatting |
| **6** | JWT Tokens in URLs/Logs | 🔴 CRITICAL | Tokens visible in server logs, Sentry, browser history | Never log tokens; use sanitized identifiers |
| **7** | No Input Sanitization Against NoSQL Injection | 🔴 CRITICAL | MongoDB injection attacks on bookings/logs collection | Validate all user inputs before MongoDB queries |
| **8** | Redis Connection Not Initialized on Startup | 🔴 CRITICAL | Silent failures if Redis unavailable; app continues without cache | Add startup event that raises error if Redis fails |
| **9** | No Graceful Shutdown Handler | 🔴 CRITICAL | Open connections leak on container termination | Add shutdown event to close DB/Redis/HTTP connections |
| **10** | Background Workers Not Supervised | 🔴 CRITICAL | Workers die silently; no restart mechanism; no dead-letter queue | Use `APScheduler`, `Celery`, or managed job queue (AWS SQS, RabbitMQ) |

---

## 🟠 MODERATE ISSUES (Implement Before Production)

### 1️⃣ **Infrastructure & Connection Management**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **1.1** | PostgreSQL Pool Exhaustion Risk | 🟠 MODERATE | `pool_size=50` + `max_overflow=200` may lead to connection starvation under load | Monitor pool utilization; add connection pool metrics; reduce overflow to 50 |
| **1.2** | No Connection Timeout on Client Disconnects | 🟠 MODERATE | Orphaned connections hang for 30s (`pool_timeout`) | Add `pool_pre_ping=True` (already done ✅) but monitor slow queries |
| **1.3** | MongoDB Not Pooling | 🟠 MODERATE | Motor may create new connections per request | Use `maxPoolSize=50, minPoolSize=10` in `MONGO_URI` |
| **1.4** | Redis Connection Silently Fails | 🟠 MODERATE | If Redis unavailable, app continues without caching | Add startup validation; log Redis health at `/health` endpoint |
| **1.5** | No Database Read Replicas | 🟠 MODERATE | All queries hit primary (no read scaling) | Consider read-only replicas for reports/analytics |
| **1.6** | No Multi-Region Failover | 🟠 MODERATE | Single DB region = single point of failure | Plan: RTO=30min, RPO=5min (backup strategy undefined) |

---

### 2️⃣ **Security Hardening**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **2.1** | JWT No Rotation/Revocation Mechanism | 🟠 MODERATE | Tokens valid until expiry; no way to revoke lost tokens immediately | Add Redis blacklist + pre-logout window (already partially done, needs verification) |
| **2.2** | Refresh Tokens Stored in Sessions Table | 🟠 MODERATE | No encryption; database breach = all tokens compromised | Encrypt refresh tokens with `cryptography.Fernet` |
| **2.3** | Environment Variables Exposed | 🟠 MODERATE | `.env` in git history or accidentally committed | Use `.env.example` + add to `.gitignore` (verify: check git history) |
| **2.4** | Password Hash Not Salted Per-User | 🟠 MODERATE | Custom hash using PBKDF2; verify salt randomness | Switch to `argon2-cffi` or ensure bcrypt is used |
| **2.5** | No Secrets Rotation Policy | 🟠 MODERATE | `SECRET_KEY` never rotated; if compromised, all tokens at risk | Implement key rotation (quarterly) + graceful dual-key support |
| **2.6** | OTP Sent via Email (No HTTPS) | 🟠 MODERATE | Email is plaintext; OTP may be logged upstream | Ensure SMTP over TLS; never log OTP |
| **2.7** | No CSRF Protection | 🟠 MODERATE | State-changing endpoints (POST/PUT/DELETE) not CSRF-protected | Add `CsrfProtectMiddleware` for cookie-based requests |
| **2.8** | No Content-Type Validation | 🟠 MODERATE | File uploads may bypass validation | Validate MIME types + scan with antivirus in production |
| **2.9** | SQL Parameterization Good but Verify | 🟠 MODERATE | SQLAlchemy ORM prevents SQL injection; but raw `.text()` queries risky | Audit for `.text()` or `.execute()` with user input |
| **2.10** | No API Key Management | 🟠 MODERATE | Third-party integrations may need API keys (payments, SMS) | Use AWS Secrets Manager / HashiCorp Vault |

---

### 3️⃣ **Performance & Scalability**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **3.1** | No Query Indexing Strategy | 🟠 MODERATE | Bookings by status, rooms by availability may scan table | Audit slow queries; add indexes on `status`, `room_status`, `booking_date` |
| **3.2** | Potential N+1 Query Problem | 🟠 MODERATE | Reviews with room details may load room per review | Use SQLAlchemy `selectinload()` / `joinedload()` |
| **3.3** | No Pagination Enforced | 🟠 MODERATE | `/api/reviews/` allows returning all reviews | Add `limit=100` default; document pagination limits |
| **3.4** | Redis Cache Invalidation Manual | 🟠 MODERATE | `invalidate_pattern()` inefficient for large patterns | Use tagged cache or event-driven invalidation |
| **3.5** | No Cache Warming | 🟠 MODERATE | Cold start = poor performance on first request | Pre-load room types, amenities on startup |
| **3.6** | No Read-Write Splitting | 🟠 MODERATE | Reports query primary DB = blocking write transactions | Route analytics to replica or separate reporting DB |
| **3.7** | No Async Task Queue | 🟠 MODERATE | Background workers in `asyncio.create_task()` = not distributed | Use Celery + Redis for distributed task execution |
| **3.8** | PDF Generation Sync | 🟠 MODERATE | Report generation blocks request thread | Move to async task queue (reportlab is CPU-bound) |
| **3.9** | No Query Result Caching | 🟠 MODERATE | Rooms list cached but not invalidated on room creation | Implement versioned cache keys |
| **3.10** | Eager Loading Disabled | 🟠 MODERATE | `expire_on_commit=False` = extra queries if lazy loading | Consider explicit eager loading |

---

### 4️⃣ **Observability & Monitoring**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **4.1** | No Structured Logging | 🟠 MODERATE | `print()` statements not parseable; no JSON logs | Use `loguru` with JSON formatter + send to ELK/Datadog |
| **4.2** | No Error Tracking (Sentry) | 🟠 MODERATE | 500 errors not tracked centrally | Integrate `sentry-sdk` + configure DSN |
| **4.3** | No APM (Application Performance Monitoring) | 🟠 MODERATE | No visibility into slow endpoints, DB query times | Use DataDog APM, New Relic, or Elastic APM |
| **4.4** | No Metrics/Prometheus | 🟠 MODERATE | No request duration, error rate, DB connection metrics | Add `prometheus-client` + expose `/metrics` endpoint |
| **4.5** | No Health Check Endpoint | 🟠 MODERATE | K8s can't determine if app is healthy | Add `GET /health` returning DB + Redis + Mongo status |
| **4.6** | No Request ID Tracing | 🟠 MODERATE | Can't correlate logs across services | Add request ID header + log propagation |
| **4.7** | No Distributed Tracing | 🟠 MODERATE | Multi-step transactions (booking → payment → notification) not traced | Use OpenTelemetry + Jaeger backend |
| **4.8** | Logging Middleware Not Configurable | 🟠 MODERATE | Can't filter sensitive endpoints (passwords, tokens) | Add logging level config + endpoint whitelist |
| **4.9** | No Audit Trail for Sensitive Operations | 🟠 MODERATE | Who deleted a booking? When was payment made? | Centralize audit logging (partially done in services) |
| **4.10** | No Log Retention Policy | 🟠 MODERATE | Logs grow indefinitely; old logs not archived | Configure log rotation + S3 archival |

---

### 5️⃣ **Database & Schema Health**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **5.1** | No Alembic Migration Versioning CI/CD | 🟠 MODERATE | Migrations not auto-validated in PR; schema drift possible | Add migration linting; auto-test migrations in CI |
| **5.2** | No Foreign Key Constraint Verification | 🟠 MODERATE | Orphaned records possible if FK constraints not enforced | Audit schema: enable `DEFERRABLE INITIALLY DEFERRED` for complex ops |
| **5.3** | No Deadlock Detection | 🟠 MODERATE | Concurrent updates to rooms/bookings may deadlock | Add exponential backoff + deadlock retry logic |
| **5.4** | MongoDB Write Concern Not Set | 🟠 MODERATE | Logs collection may lose data on crash | Set `writeConcern.j=true` (journaled) for audit logs |
| **5.5** | No MongoDB Transactions | 🟠 MODERATE | Multi-document updates (booking + room) not atomic | Use session transactions for critical operations |
| **5.6** | No Backup Automation | 🟠 MODERATE | Backup endpoint exists but no scheduled backups | Add APScheduler task for daily backups → S3 |
| **5.7** | No Restore Testing | 🟠 MODERATE | Backups exist but never tested for recovery | Weekly restore drills; document RTO/RPO |
| **5.8** | No Schema Versioning | 🟠 MODERATE | Can't easily rollback schema changes | Use Alembic downgrade path for all migrations |
| **5.9** | No Table Statistics | 🟠 MODERATE | Query planner may choose suboptimal plans | Run `ANALYZE` periodically on PostgreSQL |
| **5.10** | Connection Pool Not Sized for Peak Load | 🟠 MODERATE | `pool_size=50` may be too small for 100+ concurrent users | Load test to find optimal pool size |

---

### 6️⃣ **MongoDB-Specific Practices**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **6.1** | No Index Definitions in Code | 🟠 MODERATE | Indexes created manually; not in migration history | Use MongoDB Atlas or pymongo `create_index()` in startup event |
| **6.2** | No TTL Indexes for OTP/Sessions | 🟠 MODERATE | Expired OTPs accumulate in logs collection | Add `expireAfterSeconds=600` on verification timestamps |
| **6.3** | No Query Projection | 🟠 MODERATE | Fetching entire documents; may transfer extra data | Project only needed fields in find queries |
| **6.4** | No Aggregation Pipeline Optimization | 🟠 MODERATE | Complex reports may scan entire collection | Ensure `$match` early in pipeline; use `$facet` for multiple aggregations |
| **6.5** | Read Preference Not Optimized | 🟠 MODERATE | All reads from primary (no replica read scale) | Consider `secondaryPreferred` for analytics |
| **6.6** | No Change Streams Monitoring | 🟠 MODERATE | Can't react to log collection updates in real-time | Use MongoDB Change Streams for audit log processing |
| **6.7** | Document Size Not Monitored | 🟠 MODERATE | Booking documents with 50+ reviews may exceed 16MB limit | Use references for large sub-documents |
| **6.8** | No Schema Validation | 🟠 MODERATE | Random fields can be inserted | Use `$jsonSchema` validator on collections |

---

### 7️⃣ **Redis & Caching**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **7.1** | No Cache Hit/Miss Metrics | 🟠 MODERATE | Can't optimize cache strategy | Log cache operations; track hit ratio |
| **7.2** | TTL Not Consistent | 🟠 MODERATE | Different TTLs across features; stale data unpredictable | Define TTL by data type: rooms=1hr, reviews=24hr, availability=5min |
| **7.3** | No Eviction Policy Specified | 🟠 MODERATE | May use `noeviction` (cache full = errors) | Set `maxmemory-policy=allkeys-lru` or `volatile-ttl` |
| **7.4** | No Connection Pooling in Production | 🟠 MODERATE | Single connection to Redis = bottleneck | Use `redis.ConnectionPool` with `max_connections=50` |
| **7.5** | Redis Persistence Not Configured | 🟠 MODERATE | Data lost on restart (acceptable for cache, not for sessions) | Use RDB snapshots + AOF for production |
| **7.6** | No Replica Failover | 🟠 MODERATE | Single Redis instance = SPOF | Plan: Redis Sentinel or Cluster for HA |
| **7.7** | Silent Cache Misses | 🟠 MODERATE | Code tolerates Redis errors; cache silently disabled | Distinguish cache miss vs. Redis error |
| **7.8** | No Cache Key Versioning | 🟠 MODERATE | Backward-incompatible data format = stale cache hit | Prefix cache keys with version: `v2:rooms:123` |

---

### 8️⃣ **Deployment Architecture**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **8.1** | No NGINX/Traefik Reverse Proxy Config | 🟠 MODERATE | No request buffering, compression, or SSL termination | Add reverse proxy: NGINX + SSL certificates |
| **8.2** | No Load Balancer Health Checks | 🟠 MODERATE | Dead instances may receive traffic | Implement `/health` endpoint; configure LB checks |
| **8.3** | No Graceful Shutdown | 🟠 MODERATE | SIGTERM may kill in-flight requests | Add shutdown middleware + wait for pending tasks |
| **8.4** | No Rolling Deployment Strategy | 🟠 MODERATE | Downtime during deployments | Use Blue-Green or Canary deployment |
| **8.5** | Uvicorn Single-Process | 🟠 MODERATE | Only 1 CPU core used; limited to ~100 req/s | Use `--workers=N` or Gunicorn with multiple workers |
| **8.6** | No Container Security | 🟠 MODERATE | No resource limits; root user inside container | Use non-root user; set `limits.memory=512Mi`, `limits.cpu=500m` |
| **8.7** | No Config Management | 🟠 MODERATE | Env vars scattered; no centralized config | Use ConfigMap (K8s) or AWS Systems Manager Parameter Store |
| **8.8** | No API Versioning Strategy | 🟠 MODERATE | Breaking changes = client breakage | Plan: `/api/v1/*` for future-proof versioning |
| **8.9** | No Blue-Green or Canary Deployment | 🟠 MODERATE | All traffic cuts over instantly | Implement gradual rollout (10% → 50% → 100%) |
| **8.10** | No Reverse Proxy Security Headers | 🟠 MODERATE | Missing `X-Frame-Options`, `X-Content-Type-Options`, `CSP` | Add security headers middleware |

---

### 9️⃣ **Code Architecture & Resilience**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **9.1** | No Circuit Breaker for External APIs | 🟠 MODERATE | Payments API down = whole booking fails | Use `pybreaker` or `tenacity` with circuit breaker |
| **9.2** | No Retry Policy on Transient Errors | 🟠 MODERATE | Network glitch = request failure | Add exponential backoff (3 retries, 1s/2s/4s) |
| **9.3** | No Compensation Logic for Saga Patterns | 🟠 MODERATE | Partial failures (payment OK, notification fails) not compensated | Implement compensating transactions (e.g., refund if notify fails) |
| **9.4** | Background Workers in asyncio Tasks | 🟠 MODERATE | No dead-letter handling; failed tasks disappear | Use Celery + Redis for robust task queue |
| **9.5** | No Idempotency Keys | 🟠 MODERATE | Duplicate POST requests = duplicate bookings | Add `idempotency-key` header handling |
| **9.6** | Async Task Errors Silent | 🟠 MODERATE | Unlock worker fails silently; rooms never released | Add error logging + alerting to Sentry |
| **9.7** | No Timeout on External API Calls | 🟠 MODERATE | Payment gateway hangs = request timeout (no default) | Set `httpx.timeout=30s` explicitly |
| **9.8** | No Bulkhead Pattern | 🟠 MODERATE | One slow endpoint = all workers busy | Use ThreadPoolExecutor or limit concurrent requests |
| **9.9** | No Backpressure Handling | 🟠 MODERATE | If DB slow, queue grows unbounded | Implement queue size limits + 429 responses |
| **9.10** | No Dependency Injection for Testing | 🟠 MODERATE | Database dependency hard-coded; hard to mock | Use `Depends()` more consistently; inject config |

---

### 🔟 **Code Quality & Developer Experience**

| # | Issue | Severity | Note | Fix |
|---|-------|----------|------|-----|
| **10.1** | No Linting (ruff/black) | 🟠 MODERATE | Code style inconsistent; unused imports | Add `ruff check .` + `black --check .` in CI |
| **10.2** | No Type Hints in Services | 🟠 MODERATE | Services lack return type hints | Run `mypy --strict .` to catch type issues |
| **10.3** | No Pre-commit Hooks | 🟠 MODERATE | Bad code merged before review | Add `.pre-commit-config.yaml` with linting hooks |
| **10.4** | No Unit Tests | 🟠 MODERATE | No regression detection; risky refactoring | Add pytest with >80% coverage target |
| **10.5** | No Integration Tests | 🟠 MODERATE | DB interactions untested | Add `pytest-asyncio` tests with test DB |
| **10.6** | No Smoke Tests in Production | 🟠 MODERATE | Deployments untested in live env | Add Cypress/Playwright smoke tests post-deployment |
| **10.7** | No API Contract Testing | 🟠 MODERATE | Client-server API mismatch possible | Use Pact or OpenAPI-based contract tests |
| **10.8** | No CI/CD Pipeline | 🟠 MODERATE | No automated testing/deployment | Set up GitHub Actions / GitLab CI |
| **10.9** | No Documentation of API Changes | 🟠 MODERATE | Breaking changes not communicated | Document changes in CHANGELOG.md |
| **10.10** | No Changelog | 🟠 MODERATE | Release notes incomplete | Maintain CHANGELOG.md with semver |

---

## 🟢 RECOMMENDED ADDITIONS (Optional but Strongly Advised)

| # | Feature | Priority | Effort | Benefit |
|---|---------|----------|--------|---------|
| **11.1** | Feature Flags | MEDIUM | 2 days | Gradual rollout; quick rollback |
| **11.2** | Database Query Analytics | MEDIUM | 1 day | Identify slow queries; optimize indexes |
| **11.3** | Cost Attribution | MEDIUM | 3 days | Track per-tenant costs (if multi-tenant) |
| **11.4** | Synthetic Monitoring | LOW | 2 days | Proactive detection of failures |
| **11.5** | Runbooks & Dashboards | HIGH | 5 days | Operational readiness; faster MTTR |
| **11.6** | GraphQL Gateway (Optional) | LOW | 5 days | Alternative to REST; enables flexible queries |
| **11.7** | Event Sourcing (Optional) | LOW | 10 days | Audit trail; event replay capability |
| **11.8** | API Rate Limiting per Tenant | MEDIUM | 3 days | Fair usage; prevent abuse |
| **11.9** | Multi-Tenancy Support | MEDIUM | 7 days | Scalability for SaaS model |
| **11.10** | WebSocket Support | LOW | 4 days | Real-time notifications; live updates |

---

## 📊 Detailed Recommendations by Category

### 1. **Immediate Security Fixes** (Week 1)

```python
# ✅ Fix 1: Restrict CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"],  # NOT "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)

# ✅ Fix 2: Add Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@auth_router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    # 5 attempts per minute per IP
    pass

# ✅ Fix 3: Add HTTPS Redirect + Security Headers
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ✅ Fix 4: Structured Logging
from loguru import logger
import sys

logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="{message}",
    serialize=True,  # JSON format
    level="INFO"
)

# ✅ Fix 5: Graceful Shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await disconnect_redis(app)
    await engine.dispose()
    logger.info("✅ App shut down gracefully")

# ✅ Fix 6: Health Endpoint
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Check PostgreSQL
        await db.execute(select(1))
        
        # Check Redis
        if redis:
            await redis.ping()
        
        # Check MongoDB
        await get_database().client.server_info()
        
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503
```

---

### 2. **Database Optimization** (Week 2)

```sql
-- ✅ Add Indexes
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_user_id ON bookings(user_id);
CREATE INDEX idx_rooms_status ON rooms(room_status);
CREATE INDEX idx_rooms_type_id ON rooms(room_type_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(access_token_expires_at);

-- ✅ Add Foreign Key Constraints
ALTER TABLE bookings ADD CONSTRAINT fk_booking_user 
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

-- ✅ Enable Query Logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
RELOAD;

-- ✅ MongoDB TTL Index
db.verifications.createIndex({"expires_at": 1}, {expireAfterSeconds: 0})
```

---

### 3. **Monitoring & Observability Stack** (Week 3)

```python
# ✅ Add Sentry Integration
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=0.1,  # 10% of requests
    environment=os.getenv("ENVIRONMENT", "production"),
)

# ✅ Add Prometheus Metrics
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

@app.get("/metrics")
async def metrics():
    return generate_latest()

# ✅ Add Structured Logging with Request ID
from uuid import uuid4

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        logger.info(f"Request START: {request.method} {request.url.path} (ID: {request_id})")
        response = await call_next(request)
        logger.info(f"Request END: {request.method} {request.url.path} (ID: {request_id}, Status: {response.status_code})")
        response.headers["X-Request-ID"] = request_id
        return response
```

---

### 4. **Resilience & Error Handling** (Week 4)

```python
# ✅ Add Circuit Breaker for External APIs
from pybreaker import CircuitBreaker

payment_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    listeners=[lambda cb, *args: logger.error(f"Circuit breaker open: {cb.name}")]
)

async def call_payment_gateway(booking_id):
    @payment_breaker
    async def _call():
        async with httpx.AsyncClient(timeout=30) as client:
            return await client.post("https://payment-api.com/process", ...)
    
    return await _call()

# ✅ Add Retry Logic with Exponential Backoff
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def create_booking_with_retry(db, booking_data):
    try:
        return await bookings_service.create(db, booking_data)
    except Exception as e:
        logger.error(f"Booking creation failed: {e}")
        raise

# ✅ Add Idempotency Support
from functools import wraps

IDEMPOTENCY_STORE = {}  # In production: Redis

@app.post("/bookings/")
async def create_booking(
    booking: BookingCreate,
    idempotency_key: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if idempotency_key and idempotency_key in IDEMPOTENCY_STORE:
        return IDEMPOTENCY_STORE[idempotency_key]
    
    result = await bookings_service.create(db, booking)
    
    if idempotency_key:
        IDEMPOTENCY_STORE[idempotency_key] = result
    
    return result

# ✅ Add Compensation Logic for Sagas
async def create_booking_saga(db, booking_data):
    """Multi-step booking: Reserve room → Process payment → Send notification"""
    room_reservation = None
    payment = None
    
    try:
        # Step 1: Reserve Room
        room_reservation = await room_service.reserve(db, booking_data.room_id)
        
        # Step 2: Process Payment
        payment = await payment_service.charge(db, booking_data.payment_info)
        
        # Step 3: Notify User
        await notification_service.send_confirmation(booking_data.user_id)
        
        return {"status": "success", "booking_id": room_reservation.booking_id}
    
    except Exception as e:
        logger.error(f"Booking saga failed: {e}")
        
        # Compensate: Rollback in reverse order
        if payment:
            await payment_service.refund(payment.payment_id)
        
        if room_reservation:
            await room_service.release_hold(room_reservation.room_id)
        
        raise
```

---

### 5. **Deployment Configuration** (Week 5)

```yaml
# ✅ docker-compose.yml (for local testing)
version: '3.9'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db
      - REDIS_URL=redis://redis:6379
      - MONGO_URI=mongodb://mongo:27017
    depends_on:
      - postgres
      - redis
      - mongo
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

  mongo:
    image: mongo:6
    environment:
      - MONGO_INITDB_DATABASE=hotel_booking

volumes:
  postgres_data:
```

```dockerfile
# ✅ Dockerfile (Multi-stage build)
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy from builder
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser app/ /app/

USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```yaml
# ✅ kubernetes.yaml (K8s Deployment)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hotel-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hotel-api
  template:
    metadata:
      labels:
        app: hotel-api
    spec:
      containers:
      - name: api
        image: your-registry/hotel-api:v1.0.0
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: redis-config
              key: url
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]
```

---

### 6. **CI/CD Pipeline** (Week 6)

```yaml
# ✅ .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov ruff black mypy
    
    - name: Lint
      run: |
        ruff check .
        black --check .
        mypy app --strict
    
    - name: Run tests
      run: pytest tests/ --cov=app --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:test@localhost/test_db
        REDIS_URL: redis://localhost:6379
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build and push Docker image
      run: |
        docker build -t your-registry/hotel-api:${{ github.sha }} .
        docker push your-registry/hotel-api:${{ github.sha }}
    
    - name: Deploy to K8s
      run: |
        kubectl set image deployment/hotel-api \
          api=your-registry/hotel-api:${{ github.sha }}
```

---

### 7. **Testing Strategy** (Week 7)

```python
# ✅ tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture
async def test_db():
    """Provides test database session"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        yield session
    
    await engine.dispose()

@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)

# ✅ tests/test_authentication.py
@pytest.mark.asyncio
async def test_signup_success(test_db):
    payload = UserCreate(
        full_name="John Doe",
        email="john@example.com",
        password="SecurePass123!",
        phone_number="9876543210"
    )
    
    user = await signup(test_db, payload)
    
    assert user.email == "john@example.com"
    assert user.user_id is not None

@pytest.mark.asyncio
async def test_login_success(test_db):
    # Setup
    user = await create_user(test_db, ...)
    
    # Test
    token_response = await login_flow(test_db, user.email, "password")
    
    assert token_response.access_token is not None
    assert token_response.refresh_token is not None

# ✅ tests/test_bookings.py
@pytest.mark.asyncio
async def test_create_booking_with_idempotency(test_db, client):
    payload = {"room_id": 1, "check_in": "2025-12-01", "check_out": "2025-12-05"}
    idempotency_key = "test-booking-123"
    
    # First request
    resp1 = client.post(
        "/bookings/",
        json=payload,
        headers={"Idempotency-Key": idempotency_key}
    )
    
    # Second request (should return same)
    resp2 = client.post(
        "/bookings/",
        json=payload,
        headers={"Idempotency-Key": idempotency_key}
    )
    
    assert resp1.json()["booking_id"] == resp2.json()["booking_id"]
```

---

## 📋 Implementation Roadmap

### **Phase 1: Emergency Security Fixes** (Week 1)
- [ ] Restrict CORS to allowed origins
- [ ] Add rate limiting on auth endpoints
- [ ] Add HTTPS redirect middleware
- [ ] Add security headers
- [ ] Fix logging (no token exposure)
- [ ] Add graceful shutdown

### **Phase 2: Core Observability** (Week 2–3)
- [ ] Add Sentry integration
- [ ] Add Prometheus metrics
- [ ] Add structured JSON logging
- [ ] Add request tracing
- [ ] Add health check endpoint
- [ ] Configure alert thresholds

### **Phase 3: Database Hardening** (Week 4)
- [ ] Add query indexes
- [ ] Enable query logging
- [ ] Set up backup automation
- [ ] Configure MongoDB write concern
- [ ] Test disaster recovery

### **Phase 4: Resilience Patterns** (Week 5–6)
- [ ] Add circuit breaker pattern
- [ ] Add retry logic with exponential backoff
- [ ] Implement idempotency keys
- [ ] Add saga compensation logic
- [ ] Convert background workers to Celery

### **Phase 5: Deployment Infrastructure** (Week 7–8)
- [ ] Create Docker image + docker-compose
- [ ] Set up K8s manifests
- [ ] Configure reverse proxy (NGINX)
- [ ] Set up CI/CD pipeline
- [ ] Load testing & capacity planning

### **Phase 6: Testing & Documentation** (Week 9–10)
- [ ] Add unit tests (>80% coverage)
- [ ] Add integration tests
- [ ] Add API contract tests
- [ ] Add smoke tests for production
- [ ] Write runbooks & dashboards

---

## 🎯 Success Criteria for Production Readiness

| Criterion | Target | Status |
|-----------|--------|--------|
| Security: Rate limiting | 5/min auth endpoints | ❌ |
| Performance: P99 latency | <500ms | ⚠️ Unknown |
| Availability: Uptime SLA | 99.9% | ❌ |
| Observability: Error tracking | 100% of 5xx errors | ❌ |
| Testing: Code coverage | >80% | ❌ |
| Deployment: Zero-downtime | Blue-green deployment | ❌ |
| Backups: RPO | 4 hours max data loss | ⚠️ Manual |
| Incident Response: MTTR | <15 minutes | ❌ |

---

## 📚 Recommended Libraries & Tools

```bash
# Security
pip install slowapi             # Rate limiting
pip install cryptography        # Token encryption
pip install python-dotenv       # Env management (already done)

# Observability
pip install sentry-sdk          # Error tracking
pip install prometheus-client   # Metrics
pip install python-json-logger  # JSON logging
pip install opentelemetry-api   # Distributed tracing

# Resilience
pip install pybreaker           # Circuit breaker
pip install tenacity            # Retry logic
pip install redis               # Redis client (already done)

# Testing
pip install pytest              # Unit testing
pip install pytest-asyncio      # Async test support
pip install pytest-cov          # Coverage reporting
pip install factory-boy         # Test fixtures

# Code Quality
pip install ruff                # Fast linting
pip install black               # Code formatting
pip install mypy                # Type checking
pip install pre-commit          # Git hooks

# Deployment
pip install gunicorn            # Production ASGI server
pip install python-multipart    # File upload (already done)

# Task Queue (Important!)
pip install celery              # Distributed tasks
pip install celery-beat         # Scheduler
```

---

## ⚡ Quick Wins (High Impact, Low Effort)

1. **Add `/health` endpoint** (1 hour)
2. **Restrict CORS** (30 minutes)
3. **Add rate limiting** (1 hour)
4. **Structured logging** (2 hours)
5. **Add database indexes** (1 hour)
6. **Graceful shutdown** (1 hour)
7. **Redis health check** (1 hour)
8. **Security headers** (1 hour)
9. **HTTPS redirect** (30 minutes)
10. **Request ID tracing** (2 hours)

---

## 🔗 External Resources

- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/advanced/security/)
- [OWASP Top 10 API Security](https://owasp.org/www-project-api-security/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [MongoDB Best Practices](https://docs.mongodb.com/manual/administration/analyzing-mongodb-performance/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [The Twelve-Factor App](https://12factor.net/)

---

## Conclusion

Your backend has **solid fundamentals** but needs **hardening across security, observability, and resilience**. Prioritize the 10 critical issues first, then work through the moderate improvements systematically. Allocate **8–10 weeks** for production readiness, with parallel workstreams on security, testing, and deployment infrastructure.

**Next Step:** Schedule a team sync to review this audit and create a detailed sprint plan.

---

**Report Generated:** November 11, 2025  
**Audit Level:** Comprehensive (Architecture + Code Review)  
**Recommendations:** 60+ actionable items across 15 categories
