# Nethical Recon Worker

Asynchronous task execution and scheduling system for Nethical Recon.

## Overview

The worker module provides distributed task queue capabilities using Celery and Redis, enabling scalable and reliable execution of security scans with comprehensive policy enforcement.

## Components

### Task Queue (Celery)
- **run_scan_job** - Orchestrate complete scan jobs
- **run_tool** - Execute individual security tools
- **normalize_results** - Parse and normalize tool output
- **generate_report** - Create scan reports

### Scheduler (Celery Beat)
- Periodic baseline updates
- Recurring scans
- Cron-like scheduling

### Policy Engine
- Rate limiting (token bucket)
- Concurrency controls
- Network allowlist/denylist
- High-risk tool approval
- YAML configuration

## Quick Start

### 1. Start Infrastructure

```bash
# Start Redis and PostgreSQL
docker-compose up -d
```

### 2. Start Worker

```bash
# Start worker with 4 processes
nethical-worker start --concurrency 4

# Or with specific queues
nethical-worker start --concurrency 4 --queues scans,tools
```

### 3. Start Scheduler (Optional)

```bash
# Start Celery Beat in separate terminal
nethical-worker beat
```

### 4. Submit Jobs

```bash
# Submit a scan job
nethical job submit example.com --name "Test Scan" --tools nmap

# Check status
nethical job status <job-id>
```

## Configuration

### Environment Variables

```bash
# Redis connection
export NETHICAL_REDIS_URL="redis://localhost:6379/0"

# Database connection
export NETHICAL_DATABASE_URL="postgresql://user:pass@localhost/dbname"

# Policy configuration
export NETHICAL_POLICY_CONFIG="policy.yaml"

# Approve high-risk tools
export NETHICAL_APPROVE_SQLMAP="true"
```

### Policy Configuration (policy.yaml)

```yaml
rate_limit:
  requests_per_second: 1.0
  burst_size: 5

concurrency:
  max_parallel_jobs: 5
  max_parallel_tools: 3
  max_parallel_tools_per_job: 2

network:
  allowlist:
    - "192.168.0.0/16"
    - "10.0.0.0/8"
  denylist:
    - "127.0.0.0/8"
  require_explicit_approval: true

tools:
  high_risk_tools:
    - "metasploit"
    - "sqlmap"
  require_approval_for_high_risk: true
```

## CLI Commands

### Worker Management

```bash
# Start worker
nethical-worker start [--concurrency N] [--queues Q1,Q2]

# Start scheduler
nethical-worker beat

# Check status
nethical-worker status

# Show active tasks
nethical-worker active

# Purge pending tasks
nethical-worker purge [--force]

# Show policy stats
nethical-worker policy-stats
```

### Job Management

```bash
# Submit job
nethical job submit TARGET --name NAME --tools T1,T2

# Check status
nethical job status JOB_ID

# List jobs
nethical job list [--limit N]

# View logs
nethical job logs JOB_ID [--tool TOOL]
```

## Architecture

```
┌─────────────┐
│     CLI     │ Submit jobs
└──────┬──────┘
       │
       v
┌─────────────┐
│    Redis    │ Message broker
│   (Queue)   │
└──────┬──────┘
       │
       v
┌─────────────┐     ┌──────────────┐
│   Worker    │────>│ Policy Engine│
│  (Celery)   │     └──────────────┘
└──────┬──────┘
       │
       v
┌─────────────┐
│  Database   │ Store results
│ (SQLite/PG) │
└─────────────┘
```

## Task Flow

1. **Job Submission**
   - CLI creates ScanJob in database
   - Submits `run_scan_job` task to queue
   - Returns job ID to user

2. **Job Execution**
   - Worker picks up job from queue
   - Policy engine validates job
   - Submits individual tool tasks

3. **Tool Execution**
   - Worker executes tool command
   - Captures stdout/stderr
   - Creates ToolRun record

4. **Result Processing**
   - Parser normalizes tool output
   - Creates Finding records
   - Links to Evidence

5. **Report Generation**
   - Aggregates findings
   - Generates report file
   - Updates job status

## Policy Enforcement

### Rate Limiting
Token bucket algorithm prevents overwhelming targets:
- Configure requests per second
- Burst size for temporary spikes
- Per-resource tracking

### Concurrency
Multiple levels of concurrency control:
- Max parallel jobs (default: 5)
- Max parallel tools (default: 3)
- Max tools per job (default: 2)

### Network Access
Control which targets can be scanned:
- **Allowlist** - Explicit permission required
- **Denylist** - Always blocked (localhost, link-local)
- IPv4/IPv6 CIDR support

### Tool Restrictions
Prevent misuse of dangerous tools:
- High-risk tools list (sqlmap, metasploit, etc.)
- Explicit approval required via env vars
- Disabled tools list

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/test_policy.py -v

# With coverage
pytest tests/test_policy.py --cov=nethical_recon.worker
```

### Adding New Tasks

1. **Define task in tasks.py**:
```python
@app.task(bind=True, base=PolicyAwareTask)
def my_task(self, arg1, arg2):
    # Task implementation
    return {"status": "success"}
```

2. **Add to task routes** (optional):
```python
app.conf.task_routes = {
    "nethical_recon.worker.tasks.my_task": {"queue": "custom"},
}
```

3. **Call from anywhere**:
```python
from nethical_recon.worker.tasks import my_task

result = my_task.delay(arg1, arg2)
```

### Adding New Parsers

1. **Create parser class**:
```python
from nethical_recon.core.parsers import BaseParser

class MyToolParser(BaseParser):
    def can_parse(self, output: str) -> bool:
        return "my-tool" in output
    
    def parse(self, output: str, run_id: UUID) -> list[Finding]:
        # Parse logic
        return findings
```

2. **Register in normalize_results task**:
```python
if tool_run.tool_name == "mytool":
    parser = MyToolParser()
    findings = parser.parse(tool_run.stdout, run_id=tool_run.id)
```

## Monitoring

### Celery Monitoring

```bash
# Flower (web-based monitoring)
pip install flower
celery -A nethical_recon.worker.celery_app flower

# Visit http://localhost:5555
```

### Redis Monitoring

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Monitor commands
MONITOR

# Check queue lengths
LLEN celery
```

### Task Status

```python
from nethical_recon.worker.tasks import run_scan_job

# Get task result
result = run_scan_job.AsyncResult(task_id)
print(result.state)  # PENDING, STARTED, SUCCESS, FAILURE
print(result.result)
```

## Troubleshooting

### Worker Won't Start
- Check Redis connection: `redis-cli ping`
- Verify environment variables
- Check for port conflicts

### Tasks Not Executing
- Verify worker is running: `nethical-worker status`
- Check queue names match
- Review worker logs

### Policy Violations
- Check policy configuration
- Verify allowlist includes target
- Check tool approval env vars

### Rate Limiting Issues
- Increase `requests_per_second`
- Increase `burst_size`
- Add delays between requests

## Production Deployment

### Scaling Workers

```bash
# Multiple workers on same host
nethical-worker start --concurrency 4 &
nethical-worker start --concurrency 4 &

# Different queues per worker
nethical-worker start --queues scans &
nethical-worker start --queues tools &
```

### High Availability

- Run multiple worker instances
- Use Redis Sentinel for broker HA
- Use PostgreSQL for database
- Deploy scheduler on separate instance

### Performance Tuning

```python
# In celery_app.py
app.conf.update(
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    task_time_limit=7200,           # 2 hours for long scans
    worker_max_tasks_per_child=500, # Restart more frequently
)
```

## Security Notes

- **Never expose Redis** to public network
- **Use strong passwords** for Redis and database
- **Restrict network access** via firewall
- **Enable audit logging** in policy config
- **Rotate credentials** regularly
- **Monitor for abuse** via policy stats

## Resources

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Phase C Summary](../PHASE_C_SUMMARY.md)
- [Roadmap 3.0](../roadmap_3.md)

## License

See [LICENSE](../LICENSE) file for details.
