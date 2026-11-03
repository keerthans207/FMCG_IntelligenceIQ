"""
MongoDB database initialization.

Creates collections, validation rules, and indexes from configs/mongodb.yaml.
Safe to run repeatedly (idempotent).
"""

from __future__ import annotations

from typing import Any

import yaml
from pathlib import Path

from fmcg.config.settings import EnvSettings
from fmcg.database.connection import get_database


def _load_mongodb_yaml() -> dict[str, Any]:
    config_path = Path(__file__).resolve().parent.parent.parent.parent / "configs" / "mongodb.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def init_database(settings: EnvSettings | None = None) -> dict[str, Any]:
    """
    Initialize the MongoDB database: create collections with validators
    and indexes. Returns a summary of what was created.

    Idempotent — safe to call multiple times.
    """
    db = get_database(settings)
    config = _load_mongodb_yaml()
    collections_config = config.get("collections", {})

    existing_collections = set(db.list_collection_names())
    results: dict[str, Any] = {"collections": {}, "indexes": {}}

    for coll_name, coll_config in collections_config.items():
        # Create collection if missing
        if coll_name not in existing_collections:
            validator = coll_config.get("validator")
            if validator:
                db.create_collection(coll_name, validator=validator)
            else:
                db.create_collection(coll_name)
            results["collections"][coll_name] = "created"
        else:
            results["collections"][coll_name] = "exists"

        # Create indexes
        coll = db[coll_name]
        index_specs = coll_config.get("indexes", [])
        created_indexes: list[str] = []
        for spec in index_specs:
            keys = spec["key"]
            opts = {k: v for k, v in spec.items() if k != "key"}
            index_name = coll.create_index(list(keys.items()), **opts)
            created_indexes.append(index_name)
        results["indexes"][coll_name] = created_indexes

    return results


def health_check(settings: EnvSettings | None = None) -> dict[str, Any]:
    """Run a MongoDB health check. Returns status and server info."""
    try:
        db = get_database(settings)
        server_info = db.command("ping")
        return {
            "status": "healthy",
            "database": db.name,
            "ping": server_info,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
