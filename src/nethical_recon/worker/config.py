"""Worker configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class WorkerConfig:
    """Configuration for worker and task execution."""

    # Celery broker settings
    broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Task execution settings
    task_always_eager: bool = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
    task_eager_propagates: bool = True

    # Worker concurrency
    worker_concurrency: int = int(os.getenv("WORKER_CONCURRENCY", "4"))
    worker_prefetch_multiplier: int = int(os.getenv("WORKER_PREFETCH_MULTIPLIER", "1"))

    # Task routing
    task_routes: dict[str, dict[str, str]] | None = None

    # Task time limits (in seconds)
    task_soft_time_limit: int = int(os.getenv("TASK_SOFT_TIME_LIMIT", "3600"))  # 1 hour
    task_time_limit: int = int(os.getenv("TASK_TIME_LIMIT", "7200"))  # 2 hours

    # Result expiration (in seconds)
    result_expires: int = int(os.getenv("RESULT_EXPIRES", "86400"))  # 24 hours

    # Beat schedule settings
    beat_schedule_filename: str = os.getenv("BEAT_SCHEDULE_FILE", "/tmp/celerybeat-schedule")


def get_worker_config() -> WorkerConfig:
    """Get worker configuration."""
    return WorkerConfig()
