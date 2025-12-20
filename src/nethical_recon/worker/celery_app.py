"""Celery application configuration."""

from __future__ import annotations

import os

from celery import Celery

# Get Redis URL from environment, default to local Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "nethical_recon",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["nethical_recon.worker.tasks"],
)

# Configure Celery
celery_app.conf.update(
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Include task args in result
    # Task routing
    task_routes={
        "nethical_recon.worker.tasks.*": {"queue": "nethical"},
    },
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    # Task time limits
    task_time_limit=3600,  # Hard limit: 1 hour
    task_soft_time_limit=3300,  # Soft limit: 55 minutes
    # Task acknowledgment
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Reject if worker dies
    # Retry settings
    task_default_retry_delay=60,  # Wait 60s before retry
    task_max_retries=3,  # Max 3 retries
)
