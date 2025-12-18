"""Celery application configuration for Nethical Recon worker queue."""

from __future__ import annotations

import os

from celery import Celery

# Get Redis URL from environment or use default
REDIS_URL = os.environ.get("NETHICAL_REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery(
    "nethical_recon",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["nethical_recon.worker.tasks"],
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker settings
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_on_timeout": True,
    },
    # Task execution settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject task if worker dies
    task_track_started=True,  # Track when tasks start
    # Rate limiting and time limits (from Policy Engine)
    task_time_limit=3600,  # 1 hour hard limit per task
    task_soft_time_limit=3000,  # 50 minutes soft limit
    # Retry settings
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,  # Maximum 3 retries
    # Beat schedule (for periodic tasks)
    beat_schedule={
        # Example: Update baseline every 6 hours
        "update-baseline-every-6-hours": {
            "task": "nethical_recon.worker.tasks.update_baseline",
            "schedule": 21600.0,  # 6 hours in seconds
        },
    },
)

# Optional: Configure task routes (for multiple queues)
app.conf.task_routes = {
    "nethical_recon.worker.tasks.run_scan_job": {"queue": "scans"},
    "nethical_recon.worker.tasks.run_tool": {"queue": "tools"},
    "nethical_recon.worker.tasks.normalize_results": {"queue": "processing"},
    "nethical_recon.worker.tasks.generate_report": {"queue": "reports"},
}
