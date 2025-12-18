# Phase C Quick Start Guide

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies
```bash
pip install -e .
```

### 2. Start Redis
```bash
# Using Docker (recommended)
docker run -d --name nethical-redis -p 6379:6379 redis:7-alpine

# Or install locally
# Ubuntu: sudo apt-get install redis-server && redis-server
# macOS: brew install redis && brew services start redis
```

### 3. Initialize Database
```bash
# Run migrations
alembic upgrade head

# Or let the system auto-create tables (SQLite)
# It will create nethical_recon.db automatically
```

### 4. Start Worker
```bash
# Terminal 1
celery -A nethical_recon.worker.celery_app worker --loglevel=info
```

### 5. Submit a Job
```bash
# Terminal 2
nethical job submit example.com --name "Quick Test" --tools nmap
```

### 6. Check Status
```bash
nethical job status <job-id-from-step-5>
```

## 🎯 Common Use Cases

### Job Submission
```bash
# Basic scan
nethical job submit scanme.nmap.org --name "Nmap Scan" --tools nmap

# Multiple tools
nethical job submit example.com --name "Full Scan" --tools nmap,nikto,dirb

# With description
nethical job submit 192.0.2.10 \
  --name "Security Audit" \
  --description "Weekly security scan" \
  --tools nmap
```

### Job Monitoring
```bash
# Check specific job
nethical job status 123e4567-e89b-12d3-a456-426614174000

# List recent jobs
nethical job list --limit 20

# View job logs
nethical job logs 123e4567-e89b-12d3-a456-426614174000

# Filter logs by tool
nethical job logs 123e4567-e89b-12d3-a456-426614174000 --tool nmap
```

### Policy Examples
```bash
# Run policy engine example
python examples/policy_engine_example.py
```

## ⚙️ Configuration

### Environment Variables
```bash
# Database (default: SQLite)
export NETHICAL_DATABASE_URL="sqlite:///./nethical_recon.db"

# For PostgreSQL
export NETHICAL_DATABASE_URL="postgresql://user:pass@localhost/nethical_recon"

# Redis (default: localhost)
export NETHICAL_REDIS_URL="redis://localhost:6379/0"

# Debug mode
export NETHICAL_DEBUG="true"
```

### Custom Policy (Python)
```python
from nethical_recon.core.policy import Policy, RiskLevel

# Create custom policy
policy = Policy(
    name="my_policy",
    risk_level=RiskLevel.LOW,
    rate_limit={
        "enabled": True,
        "requests_per_second": 10.0
    },
    concurrency={
        "max_parallel_scans": 5
    }
)
```

## 🔧 Troubleshooting

### Worker Not Starting
```bash
# Check Redis connection
redis-cli ping
# Should return: PONG

# Check Python imports
python -c "from nethical_recon.worker import celery_app; print('OK')"

# Check worker with verbose logging
celery -A nethical_recon.worker.celery_app worker --loglevel=debug
```

### Jobs Not Running
```bash
# Check worker is running
celery -A nethical_recon.worker.celery_app inspect active

# Check queue length
redis-cli LLEN celery

# Check job status in database
sqlite3 nethical_recon.db "SELECT id, name, status FROM scan_jobs ORDER BY created_at DESC LIMIT 5;"
```

### Database Issues
```bash
# SQLite locked (use PostgreSQL for multi-worker)
export NETHICAL_DATABASE_URL="postgresql://user:pass@localhost/nethical_recon"
alembic upgrade head

# Reset database (WARNING: deletes all data)
rm nethical_recon.db
alembic upgrade head
```

### Policy Violations
```python
# Check what's being blocked
from nethical_recon.core.policy import PolicyEngine, create_default_policy

engine = PolicyEngine(create_default_policy())

# Test target
try:
    engine.validate_target("10.0.0.1")
except Exception as e:
    print(f"Blocked: {e}")

# Test tool
try:
    engine.validate_tool("sqlmap")
except Exception as e:
    print(f"Blocked: {e}")
```

## 📊 Monitoring

### Worker Status
```bash
# Active tasks
celery -A nethical_recon.worker.celery_app inspect active

# Worker statistics
celery -A nethical_recon.worker.celery_app inspect stats

# Registered tasks
celery -A nethical_recon.worker.celery_app inspect registered
```

### Flower Web UI (Optional)
```bash
# Install Flower
pip install flower

# Start Flower
celery -A nethical_recon.worker.celery_app flower --port=5555

# Access at http://localhost:5555
```

### Redis Monitoring
```bash
# Monitor commands
redis-cli MONITOR

# Queue length
redis-cli LLEN celery

# Result keys
redis-cli KEYS "celery-task-meta-*"
```

## 🔒 Security Best Practices

1. **Always use explicit authorization**
   - Never scan targets without written permission
   - Use require_explicit_consent: true

2. **Use network restrictions**
   - Block private networks by default
   - Use allowlist for authorized ranges

3. **Rate limit appropriately**
   - Start conservative (10 req/s)
   - Increase only with authorization

4. **Restrict high-risk tools**
   - Block metasploit, sqlmap, etc. by default
   - Require explicit approval

5. **Monitor and audit**
   - Review job logs regularly
   - Check for policy violations
   - Track all executed commands

## 📚 Additional Resources

- **Full Deployment Guide**: WORKER_DEPLOYMENT.md
- **Phase C Summary**: PHASE_C_SUMMARY.md
- **Roadmap**: roadmap_3.md
- **Examples**: examples/policy_engine_example.py

## 🆘 Getting Help

### Check Logs
```bash
# Worker logs
tail -f /var/log/celery/worker.log

# Application logs
python -c "import logging; logging.basicConfig(level=logging.DEBUG); from nethical_recon.worker import celery_app"
```

### Common Errors

**"No module named celery"**
```bash
pip install celery redis
```

**"Connection refused (Redis)"**
```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine
```

**"Database is locked"**
```bash
# Use PostgreSQL instead of SQLite
export NETHICAL_DATABASE_URL="postgresql://..."
```

**"Target is in denied network"**
```python
# Create custom policy with allowed networks
from nethical_recon.core.policy.models import Policy, NetworkPolicy

policy = Policy(
    network=NetworkPolicy(
        allow_networks=["192.0.2.0/24"],
        deny_networks=[]
    )
)
```

## 🎉 Success Checklist

- [ ] Redis is running
- [ ] Worker is running
- [ ] Database is initialized
- [ ] Job submitted successfully
- [ ] Job status shows "running" or "completed"
- [ ] Findings are generated
- [ ] No policy violations

## Next Steps

1. ✅ Phase C complete
2. ⏳ Phase D: REST API + OpenAPI
3. ⏳ Phase E: Observability (Logging + Metrics)
4. ⏳ Phase F: Docker/Kubernetes

---

**Phase C Status**: ✅ COMPLETE (2025-12-18)
