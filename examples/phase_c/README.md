# Phase C: Worker Queue + Scheduler + Concurrency Policy

This directory contains examples for Phase C features: asynchronous job processing, periodic scheduling, and policy enforcement.

## Prerequisites

```bash
# Install dependencies
pip install -e .

# Start Redis (required for worker queue)
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

## Quick Start

### 1. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Start the Worker

```bash
# Start Celery worker (in a separate terminal)
celery -A nethical_recon.worker.celery_app worker --loglevel=info --concurrency=5
```

### 3. Submit Jobs

```bash
# Using CLI
nethical job submit example.com --name "Test scan" --tools nmap,nikto

# Check status
nethical job status <job-id>

# View logs
nethical job logs <job-id>
```

### 4. Schedule Periodic Scans

```bash
# Start scheduler
nethical scheduler start

# Schedule periodic scan (every 6 hours)
nethical scheduler schedule example.com --interval 6 --tools nmap,nikto

# Schedule cron scan (daily at 2 AM)
nethical scheduler schedule test.com --cron "0 2 * * *" --tools nmap

# List scheduled jobs
nethical scheduler list

# Remove a scheduled job
nethical scheduler remove <job-id>
```

### 5. Check Policy

```bash
# Show current policy configuration
nethical policy show

# Validate if a scan is allowed
nethical policy validate 192.168.1.1 --tool nmap
```

## Examples

### Worker Queue
See `worker_example.py` for programmatic job submission:

```bash
python worker_example.py
```

### Scheduler
See `scheduler_example.py` for scheduler usage:

```bash
python scheduler_example.py
```

### Policy Engine
See `policy_example.py` for policy configuration:

```bash
python policy_example.py
```

## Configuration

### Environment Variables

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
ROE_MAX_REQUESTS_PER_SEC=10.0
ROE_MAX_CONCURRENT_TOOLS=5
ROE_MAX_CONCURRENT_JOBS=10

# Scan Limits
ROE_MAX_SCAN_DURATION=3600
ROE_MAX_PORTS=1000
ROE_MAX_THREADS=10

# Tool Authorization
ROE_REQUIRE_EXPLICIT_AUTH=true

# Network Restrictions (optional)
# ROE_ALLOWED_NETWORKS=192.168.0.0/16,10.0.0.0/8
# ROE_DENIED_NETWORKS=192.168.100.0/24
```

## Architecture

```
┌─────────────────┐
│   CLI / API     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  Policy Engine  │◄─────┤ RoE Config   │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│   Job Queue     │◄─────┤    Redis     │
│    (Celery)     │      └──────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Worker Pool    │
│  (run_tool,     │
│   normalize,    │
│   report)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│   Database      │◄─────┤  SQLite/PG   │
└─────────────────┘      └──────────────┘

         +
         
┌─────────────────┐
│   Scheduler     │
│  (APScheduler)  │
│  - Periodic     │
│  - Cron         │
│  - Baseline     │
└─────────────────┘
```

## Features

### Worker Queue
- ✅ Asynchronous job execution
- ✅ Task retry and error handling
- ✅ Distributed worker support
- ✅ Result persistence
- ✅ Job status tracking

### Scheduler
- ✅ Periodic scans (interval-based)
- ✅ Cron scans (expression-based)
- ✅ Baseline updates
- ✅ Job management (add/remove/list)

### Policy Engine
- ✅ Rate limiting
- ✅ Concurrency controls
- ✅ Tool authorization
- ✅ Network validation
- ✅ Scan configuration validation
- ✅ Environment-based configuration

## Troubleshooting

### Redis not connecting
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# Check Redis logs
tail -f /var/log/redis/redis-server.log
```

### Worker not starting
```bash
# Check Celery worker logs
celery -A nethical_recon.worker.celery_app worker --loglevel=debug

# Verify tasks are registered
celery -A nethical_recon.worker.celery_app inspect registered
```

### Policy denying scans
```bash
# Check policy configuration
nethical policy show

# Validate specific scan
nethical policy validate <target> --tool <tool>

# Adjust environment variables in .env
```

## Next Steps

- Phase D: REST API + OpenAPI
- Phase E: Observability (Logging + Metrics)
- Phase F: Docker + Kubernetes deployment

## Documentation

- [Phase C Summary](../../PHASE_C_SUMMARY.md)
- [Roadmap 3.0](../../roadmap_3.md)
- [Main README](../../README.md)
