"""Storage layer for Nethical Recon."""

from __future__ import annotations

__all__ = ["Base", "DatabaseManager", "init_db"]

from .base import Base
from .manager import DatabaseManager
from .models import (
    AssetModel,
    EvidenceModel,
    FindingModel,
    IOCModel,
    ScanJobModel,
    TargetModel,
    ToolRunModel,
)


def init_db(database_url: str = "sqlite:///nethical_recon.db") -> DatabaseManager:
    """Initialize database and return manager instance.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        DatabaseManager instance
    """
    manager = DatabaseManager(database_url)
    manager.create_tables()
    return manager
