"""Celery worker configuration."""

from __future__ import annotations

import os

from celery import Celery

# Get configuration from environment
REDIS_URL = os.getenv("NETHICAL_REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("NETHICAL_DATABASE_URL", "sqlite:///nethical_recon.db")

# Create Celery app
app = Celery(
    "nethical_recon",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["nethical_recon.worker.tasks"],
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=7200,  # 2 hours hard limit
    task_soft_time_limit=3600,  # 1 hour soft limit
    worker_prefetch_multiplier=1,  # Only fetch one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory management)
    task_acks_late=True,  # Acknowledge task after completion (for reliability)
    task_reject_on_worker_lost=True,  # Reject task if worker crashes
    result_expires=86400,  # Keep results for 24 hours
    broker_connection_retry_on_startup=True,
)

# Celery beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Add periodic tasks here
    # Example:
    # 'baseline-update': {
    #     'task': 'nethical_recon.worker.tasks.update_baseline',
    #     'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
    # },
}

if __name__ == "__main__":
    app.start()
