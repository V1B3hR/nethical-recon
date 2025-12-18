"""Scheduled scan models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ScheduleFrequency(str, Enum):
    """Frequency of scheduled scans."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # Custom cron expression


class ScheduledScan(BaseModel):
    """Represents a scheduled recurring scan."""

    id: UUID = Field(default_factory=uuid4, description="Unique schedule identifier")
    target_id: UUID = Field(..., description="Target to scan")
    name: str = Field(..., description="Schedule name")
    description: str | None = Field(None, description="Schedule description")
    frequency: ScheduleFrequency = Field(..., description="Scan frequency")
    cron_expression: str | None = Field(None, description="Custom cron expression (for CUSTOM frequency)")
    tools: list[str] = Field(..., description="Tools to run in scheduled scans")
    enabled: bool = Field(default=True, description="Whether schedule is active")
    config: dict = Field(default_factory=dict, description="Schedule configuration")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp (UTC)")
    last_run_at: datetime | None = Field(None, description="Last execution timestamp (UTC)")
    next_run_at: datetime | None = Field(None, description="Next scheduled execution (UTC)")
    created_by: str = Field(default="system", description="User who created the schedule")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "target_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Daily security scan",
                "frequency": "daily",
                "tools": ["nmap", "nikto"],
                "enabled": True,
            }
        }


def frequency_to_cron(frequency: ScheduleFrequency) -> str:
    """Convert frequency to cron expression.

    Args:
        frequency: Schedule frequency

    Returns:
        Cron expression string
    """
    if frequency == ScheduleFrequency.HOURLY:
        return "0 * * * *"  # Every hour at minute 0
    elif frequency == ScheduleFrequency.DAILY:
        return "0 2 * * *"  # Every day at 2 AM
    elif frequency == ScheduleFrequency.WEEKLY:
        return "0 2 * * 0"  # Every Sunday at 2 AM
    elif frequency == ScheduleFrequency.MONTHLY:
        return "0 2 1 * *"  # First day of month at 2 AM
    else:
        raise ValueError(f"Cannot convert {frequency} to cron, use custom expression")
