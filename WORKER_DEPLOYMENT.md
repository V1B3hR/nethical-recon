# Worker and Scheduler Deployment Guide

## Overview

Phase C introduces asynchronous job processing, scheduling, and policy enforcement using Celery and Redis.

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  CLI Client  │─────▶│ Redis Broker │◀─────│   Workers    │
└──────────────┘      └──────────────┘      └──────────────┘
                             │                      │
                             │                      ▼
                             │              ┌──────────────┐
                             └─────────────▶│   Database   │
                                            └──────────────┘
```

### Components

1. **Redis Broker**: Message queue for task distribution
2. **Celery Workers**: Process scan jobs asynchronously
3. **Celery Beat**: Periodic task scheduler
4. **Policy Engine**: Enforces Rules of Engagement
5. **Database**: Stores job status and results

## Prerequisites

### Install Redis

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Docker:**
```bash
docker run -d --name nethical-redis -p 6379:6379 redis:7-alpine
```

### Verify Redis
```bash
redis-cli ping
# Should return: PONG
```

## Configuration

### Environment Variables

Create a `.env` file:

```bash
# Database
NETHICAL_DATABASE_URL=sqlite:///./nethical_recon.db
# For PostgreSQL:
# NETHICAL_DATABASE_URL=postgresql://user:password@localhost/nethical_recon

# Redis
NETHICAL_REDIS_URL=redis://localhost:6379/0

# Debug (optional)
NETHICAL_DEBUG=false
```

### Policy Configuration

Policies are configured via Python models. Default policy is "safe and ethical":

```python
from nethical_recon.core.policy.models import Policy, RiskLevel

policy = Policy(
    name="default",
    risk_level=RiskLevel.LOW,
    rate_limit={
        "enabled": True,
        "requests_per_second": 10.0,
        "burst_size": 20
    },
    concurrency={
        "enabled": True,
        "max_parallel_scans": 5,
        "max_parallel_tools": 3
    },
    network={
        "enabled": True,
        "deny_networks": [
            "10.0.0.0/8",      # Private
            "172.16.0.0/12",   # Private
            "192.168.0.0/16",  # Private
        ],
        "require_explicit_consent": True
    }
)
```

## Starting Workers

### Development Mode

**Single worker:**
```bash
celery -A nethical_recon.worker.celery_app worker --loglevel=info
```

**With concurrency:**
```bash
celery -A nethical_recon.worker.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --pool=prefork
```

### Production Mode

**Using systemd service:**

Create `/etc/systemd/system/nethical-worker.service`:

```ini
[Unit]
Description=Nethical Recon Celery Worker
After=network.target redis.target

[Service]
Type=forking
User=nethical
Group=nethical
WorkingDirectory=/opt/nethical-recon
Environment="NETHICAL_DATABASE_URL=postgresql://user:pass@localhost/nethical_recon"
Environment="NETHICAL_REDIS_URL=redis://localhost:6379/0"
ExecStart=/opt/nethical-recon/venv/bin/celery -A nethical_recon.worker.celery_app worker \
    --pidfile=/var/run/celery/worker.pid \
    --logfile=/var/log/celery/worker.log \
    --loglevel=info \
    --concurrency=4

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nethical-worker
sudo systemctl start nethical-worker
sudo systemctl status nethical-worker
```

## Starting Scheduler (Celery Beat)

### Development Mode

```bash
celery -A nethical_recon.worker.celery_app beat --loglevel=info
```

### Production Mode

Create `/etc/systemd/system/nethical-beat.service`:

```ini
[Unit]
Description=Nethical Recon Celery Beat Scheduler
After=network.target redis.target

[Service]
Type=simple
User=nethical
Group=nethical
WorkingDirectory=/opt/nethical-recon
Environment="NETHICAL_DATABASE_URL=postgresql://user:pass@localhost/nethical_recon"
Environment="NETHICAL_REDIS_URL=redis://localhost:6379/0"
ExecStart=/opt/nethical-recon/venv/bin/celery -A nethical_recon.worker.celery_app beat \
    --pidfile=/var/run/celery/beat.pid \
    --logfile=/var/log/celery/beat.log \
    --loglevel=info

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nethical-beat
sudo systemctl start nethical-beat
sudo systemctl status nethical-beat
```

## Using the Job Queue

### Submit a Job

```bash
nethical job submit example.com --name "Example Scan" --tools nmap,nikto
```

Output:
```
✓ Created job: 123e4567-e89b-12d3-a456-426614174000
  Target: example.com
  Tools: nmap, nikto
✓ Submitted to worker queue
  Task ID: a8c3f9e1-4b2d-4e3a-8f5c-1234567890ab

Use 'nethical job status 123e4567-e89b-12d3-a456-426614174000' to check progress
```

### Check Job Status

```bash
nethical job status 123e4567-e89b-12d3-a456-426614174000
```

Output:
```
=== Job Status: Example Scan ===
ID: 123e4567-e89b-12d3-a456-426614174000
Status: RUNNING
Created: 2025-12-18 00:51:30
Started: 2025-12-18 00:51:35

=== Tool Runs (2) ===

  nmap (7.94)
    Status: completed
    Exit code: 0
    Duration: 12.34s
    Findings: 5
      high: 2
      medium: 2
      low: 1

  nikto (2.5.0)
    Status: running
    Exit code: None
```

### List Recent Jobs

```bash
nethical job list --limit 10
```

### View Job Logs

```bash
nethical job logs 123e4567-e89b-12d3-a456-426614174000
```

Or filter by tool:
```bash
nethical job logs 123e4567-e89b-12d3-a456-426614174000 --tool nmap
```

## Monitoring

### Celery Flower (Web UI)

Install Flower:
```bash
pip install flower
```

Start Flower:
```bash
celery -A nethical_recon.worker.celery_app flower --port=5555
```

Access at: http://localhost:5555

### Redis CLI

Check queue length:
```bash
redis-cli LLEN celery
```

Monitor commands:
```bash
redis-cli MONITOR
```

### Worker Status

```bash
celery -A nethical_recon.worker.celery_app inspect active
celery -A nethical_recon.worker.celery_app inspect stats
```

## Scaling

### Horizontal Scaling

Start multiple workers on different machines:

**Machine 1:**
```bash
celery -A nethical_recon.worker.celery_app worker \
    --hostname=worker1@%h \
    --concurrency=4
```

**Machine 2:**
```bash
celery -A nethical_recon.worker.celery_app worker \
    --hostname=worker2@%h \
    --concurrency=4
```

### Queue-based Scaling

Create specialized queues:

```bash
# Fast scan queue (high priority)
celery -A nethical_recon.worker.celery_app worker \
    --queues=fast \
    --concurrency=8

# Slow scan queue (low priority)
celery -A nethical_recon.worker.celery_app worker \
    --queues=slow \
    --concurrency=2
```

## Security Best Practices

### 1. Redis Security

Require password:
```bash
# /etc/redis/redis.conf
requirepass your_strong_password_here
```

Update connection:
```bash
NETHICAL_REDIS_URL=redis://:your_strong_password_here@localhost:6379/0
```

### 2. Network Isolation

- Run Redis on localhost or private network
- Use firewall rules to restrict access
- Consider Redis Sentinel for HA

### 3. Policy Enforcement

Always use network restrictions:
```python
network={
    "enabled": True,
    "allow_networks": ["192.0.2.0/24"],  # Only authorized ranges
    "deny_networks": ["10.0.0.0/8"],     # Block private networks
    "require_explicit_consent": True
}
```

### 4. Tool Restrictions

Block high-risk tools:
```python
tool={
    "enabled": True,
    "high_risk_tools": ["metasploit", "sqlmap"],
    "require_approval_for_high_risk": True
}
```

## Troubleshooting

### Workers Not Picking Up Jobs

1. Check Redis connection:
   ```bash
   redis-cli ping
   ```

2. Check worker logs:
   ```bash
   tail -f /var/log/celery/worker.log
   ```

3. Verify task registration:
   ```bash
   celery -A nethical_recon.worker.celery_app inspect registered
   ```

### Jobs Failing

1. Check job logs:
   ```bash
   nethical job logs <job_id>
   ```

2. Check policy violations:
   - Target might be in deny list
   - Tool might be restricted
   - Rate limit exceeded

3. Verify database connection:
   ```bash
   python -c "from nethical_recon.core.storage import init_database; db = init_database(); print('OK')"
   ```

### Database Locked (SQLite)

SQLite doesn't support concurrent writes well. For production:

**Switch to PostgreSQL:**
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb nethical_recon
sudo -u postgres createuser nethical --pwprompt

# Update connection string
NETHICAL_DATABASE_URL=postgresql://nethical:password@localhost/nethical_recon

# Run migrations
alembic upgrade head
```

## Performance Tuning

### Worker Concurrency

- **CPU-bound tasks**: concurrency = CPU cores
- **I/O-bound tasks**: concurrency = 2-4 × CPU cores

```bash
celery -A nethical_recon.worker.celery_app worker --concurrency=8
```

### Task Prefetch

Limit prefetch to prevent worker hoarding:
```python
# In celery_app.py
app.conf.worker_prefetch_multiplier = 1
```

### Result Backend

For large results, consider using S3 or filesystem backend:
```python
app.conf.result_backend = 'file:///var/lib/celery/results'
```

## Next Steps

- [ ] Deploy Flower for monitoring
- [ ] Set up log aggregation (ELK stack)
- [ ] Configure Prometheus metrics
- [ ] Implement scheduled scans
- [ ] Add job cancellation
- [ ] Deploy to Kubernetes

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/docs/)
- [Phase C Roadmap](../roadmap_3.md#phase-c--worker-queue--scheduler--concurrency-policy-3%E2%80%936-tyg)
