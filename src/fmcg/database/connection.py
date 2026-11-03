"""
MongoDB connection management.

Provides a thread-safe singleton client using PyMongo.
All connection parameters come from environment variables.
"""

from __future__ import annotations

from typing import Optional

from fmcg.config.settings import EnvSettings

try:
    from pymongo import MongoClient
    from pymongo.database import Database
except ImportError:
    MongoClient = None  # type: ignore[assignment,misc]
    Database = None  # type: ignore[assignment,misc]


_client: Optional["MongoClient"] = None
_settings: Optional[EnvSettings] = None


def get_mongo_client(settings: EnvSettings | None = None) -> "MongoClient":
    """
    Return a cached MongoClient singleton.

    Parameters
    ----------
    settings : EnvSettings, optional
        Configuration. If omitted, a new EnvSettings() is created
        (which reads from environment / .env).
    """
    global _client, _settings

    if MongoClient is None:
        raise ImportError("pymongo is not installed. Install requirements on the remote server.")

    if _client is not None and settings is None:
        return _client

    s = settings or EnvSettings()
    _settings = s

    uri = s.mongo_connection_uri()
    _client = MongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        retryWrites=True,
    )
    return _client


def get_database(settings: EnvSettings | None = None) -> "Database":
    """Return the configured MongoDB database object."""
    client = get_mongo_client(settings)
    s = _settings or settings or EnvSettings()
    return client[s.mongo_db_name]


def close_mongo_client() -> None:
    """Close the cached client (useful for tests and clean shutdown)."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
