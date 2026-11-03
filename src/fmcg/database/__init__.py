"""MongoDB database connection and initialization."""
from fmcg.database.connection import get_mongo_client, get_database
from fmcg.database.init_db import init_database

__all__ = ["get_mongo_client", "get_database", "init_database"]
