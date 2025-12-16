"""
Database Module for Nethical Recon
Multi-backend database support for stain storage

🗂️ FALA 6: STAIN DATABASE
"Permanent storage for marked threats across multiple backends"
"""

from .base_store import BaseStore, StoreBackend
from .sqlite_store import SQLiteStore
from .postgres_store import PostgreSQLStore
from .mysql_store import MySQLStore
from .mssql_store import MSSQLStore
from .oracle_store import OracleStore
from .db2_store import Db2Store
from .snowflake_store import SnowflakeStore
from .mongodb_store import MongoDBStore
from .redis_cache import RedisCache
from .elasticsearch_store import ElasticsearchStore
from .store_factory import StoreFactory, create_store
from .connection_pool import ConnectionPool, PooledStore

__all__ = [
    # Base classes
    "BaseStore",
    "StoreBackend",
    # Store implementations
    "SQLiteStore",
    "PostgreSQLStore",
    "MySQLStore",
    "MSSQLStore",
    "OracleStore",
    "Db2Store",
    "SnowflakeStore",
    "MongoDBStore",
    "RedisCache",
    "ElasticsearchStore",
    # Factory and utilities
    "StoreFactory",
    "create_store",
    "ConnectionPool",
    "PooledStore",
]

__version__ = "1.0.0"
