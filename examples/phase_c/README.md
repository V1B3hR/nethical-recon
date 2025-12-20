# Phase C Examples

This directory contains examples demonstrating the Phase C features: Worker Queue, Scheduler, and Policy Engine.

## Policy Engine Example

**File:** `policy_example.py`

Demonstrates how to use the Rules of Engagement (RoE) policy engine:

- Creating basic and custom policies
- Network restrictions (allowlist/denylist)
- Rate limiting
- Concurrency control
- Job validation
- Loading policies from JSON files

### Running the Example

```bash
cd /home/runner/work/nethical-recon/nethical-recon
python examples/phase_c/policy_example.py
```

## Worker Queue Usage

### Prerequisites

1. **Start Redis:**
   ```bash
   redis-server
   ```

2. **Start Celery Worker:**
   ```bash
   celery -A nethical_recon.worker.celery_app worker --loglevel=info
   ```

### Submitting Jobs via CLI

```bash
# Submit a scan job
nethical job submit example.com --name "Security Scan" --tools nmap,nikto

# Check job status
nethical job status <job-id>

# List recent jobs
nethical job list --limit 10

# View job logs
nethical job logs <job-id>
```

### Submitting Jobs Programmatically

```python
from nethical_recon.core.models import ScanJob, Target, TargetScope, TargetType
from nethical_recon.core.storage import init_database
from nethical_recon.core.storage.repository import ScanJobRepository, TargetRepository
from nethical_recon.worker.tasks import run_scan_job

# Initialize database
db = init_database()

with db.session() as session:
    # Create target
    target_repo = TargetRepository(session)
    target = Target(
        value="example.com",
        type=TargetType.DOMAIN,
        scope=TargetScope.IN_SCOPE,
    )
    target = target_repo.create(target)
    
    # Create job
    job_repo = ScanJobRepository(session)
    job = ScanJob(
        target_id=target.id,
        name="My Scan",
        tools=["nmap", "nikto"],
    )
    job = job_repo.create(job)
    session.commit()
    
    # Submit to worker queue
    task = run_scan_job.delay(str(job.id))
    print(f"Job submitted: {job.id}")
    print(f"Task ID: {task.id}")
```

## Scheduler Usage

### Starting the Scheduler

```python
from nethical_recon.worker.scheduler import ScanScheduler

scheduler = ScanScheduler()
scheduler.start()

# Schedule periodic scan (cron-style)
job_id = scheduler.schedule_periodic_scan(
    target_value="example.com",
    tools=["nmap"],
    schedule="0 */6 * * *",  # Every 6 hours
    name="Periodic Scan",
)

# Schedule interval scan
job_id = scheduler.schedule_interval_scan(
    target_value="192.168.1.0/24",
    tools=["nmap"],
    interval_hours=12,
    name="Network Sweep",
)

# List scheduled jobs
jobs = scheduler.list_scheduled_jobs()
for job in jobs:
    print(f"{job['name']}: next run at {job['next_run']}")

# Keep running
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    scheduler.shutdown()
```

## Policy Configuration

### Example policy.json

```json
{
  "name": "production",
  "description": "Production scanning policy",
  "rate_limit": {
    "requests_per_second": 1.0,
    "burst_size": 5,
    "enabled": true
  },
  "concurrency": {
    "max_parallel_tools": 3,
    "max_parallel_jobs": 5,
    "enabled": true
  },
  "network": {
    "allowed_networks": ["10.0.0.0/8", "192.168.0.0/16"],
    "denied_networks": ["10.10.10.0/24"]
  },
  "tool_policies": {
    "nmap": {
      "tool_name": "nmap",
      "risk_level": "medium",
      "requires_approval": false,
      "enabled": true,
      "max_duration_seconds": 600
    },
    "sqlmap": {
      "tool_name": "sqlmap",
      "risk_level": "high",
      "requires_approval": true,
      "enabled": true,
      "max_duration_seconds": 1800
    }
  },
  "high_risk_tools": ["sqlmap", "metasploit", "hydra"],
  "authorized_only": true,
  "audit_logging_enabled": true
}
```

### Loading Policy

```bash
# Via environment variable
export NETHICAL_POLICY_FILE=/path/to/policy.json
celery -A nethical_recon.worker.celery_app worker --loglevel=info

# Or programmatically
from nethical_recon.core.policy import PolicyEngine

engine = PolicyEngine.from_file("policy.json")
```

## Environment Variables

```bash
# Redis connection
export NETHICAL_REDIS_URL="redis://localhost:6379/0"

# Database connection
export NETHICAL_DATABASE_URL="sqlite:///nethical.db"
# Or PostgreSQL
export NETHICAL_DATABASE_URL="postgresql://user:pass@localhost/nethical"

# Policy file (optional)
export NETHICAL_POLICY_FILE="/path/to/policy.json"
```

## Testing

Run the Phase C tests:

```bash
# All policy tests
pytest tests/test_policy.py -v

# All worker tests
pytest tests/test_worker.py -v

# All Phase C tests
pytest tests/test_policy.py tests/test_worker.py -v
```

## Next Steps

- See `PHASE_C_SUMMARY.md` for complete implementation details
- Check `roadmap_3.md` for Phase D (REST API) planning
- Read the policy engine docstrings for API details
