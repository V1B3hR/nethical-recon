"""Celery application configuration."""

from __future__ import annotations

import os

from celery import Celery
from kombu import Exchange, Queue

# Get Redis URL from environment or use default
REDIS_URL = os.getenv("NETHICAL_REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery(
    "nethical_recon",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["nethical_recon.worker.tasks"],
)

# Configure Celery
app.conf.update(
    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_default_queue="default",
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("scans", Exchange("scans"), routing_key="scans"),
        Queue("tools", Exchange("tools"), routing_key="tools"),
        Queue("reports", Exchange("reports"), routing_key="reports"),
    ),
    task_routes={
        "nethical_recon.worker.tasks.run_scan_job": {"queue": "scans"},
        "nethical_recon.worker.tasks.run_tool": {"queue": "tools"},
        "nethical_recon.worker.tasks.normalize_results": {"queue": "tools"},
        "nethical_recon.worker.tasks.generate_report": {"queue": "reports"},
    },
    # Concurrency settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Task time limits
    task_soft_time_limit=600,  # 10 minutes soft limit
    task_time_limit=900,  # 15 minutes hard limit
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

if __name__ == "__main__":
    app.start()
