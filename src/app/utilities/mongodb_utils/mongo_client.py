""" 

Interact with the MongoDB database

Currently minimal in querying and whatnot, update as function gets better

"""


import os 

from dataclasses import dataclass
from enum import StrEnum

from pymongo import MongoClient
from pymongo.collection import Collection



class MongoDBCollections(StrEnum):
    JOBS = "jobs"


# For local dev, store as env vars, then github secrets, then cloud run secrets for universal runtime
@dataclass(frozen=True)
class MongoConfig:
    MONGO_URI = os.getenv("MONGO_URI", "")
    MONGO_DB = os.getenv("MONGO_DB", "document_ocr")

    def __post_init__(self):
        if not self.MONGO_URI:
            raise RuntimeError("MONGO URI Not Set, ensure connectivity to database")
        

# Seen example using global keyword instead of classes, trying out
_client: MongoClient | None = None

def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        # TODO: Add the timeout ms and whatnot later on
        _client = MongoClient(MongoConfig.MONGO_URI)
    
    return _client
    
def get_jobs_collection() -> Collection:
    client = get_mongo_client()
    return client[MongoConfig.MONGO_DB][MongoDBCollections.JOBS]



