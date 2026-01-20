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


@dataclass(frozen=True)
class MongoConfig:
    uri: str
    db_name: str = "app_events"

    @staticmethod
    def from_env() -> "MongoConfig":
        uri = os.getenv("DOC_OCR_MONGO_ATLAS_URI")
        if not uri:
            raise RuntimeError("DOC_OCR_MONGO_ATLAS_URI not set")

        db_name = os.getenv("MONGO_DB", "app_events")
        return MongoConfig(uri=uri, db_name=db_name)


class MongoStore:
    """
    Singleton for a shared MongoClient.
    One MongoClient instance per process.
    """
    _client: MongoClient | None = None
    _cfg: MongoConfig | None = None

    def __init__(self) -> None:
        raise RuntimeError(f"Do not instantiate {__class__.__name__}.")

    @classmethod
    def init(cls, cfg: MongoConfig | None = None) -> None:
        cls._cfg = cfg or MongoConfig.from_env()

    @classmethod
    def client(cls) -> MongoClient:
        if cls._cfg is None:
            cls.init()

        if cls._client is None:
            if cls._cfg is None:
                raise RuntimeError("MongoStore config not initialized")

            cls._client = MongoClient(
                cls._cfg.uri,
                serverSelectionTimeoutMS=5000,
            )
        return cls._client

    @classmethod
    def collection(cls, name: MongoDBCollections) -> Collection:
        if cls._cfg is None:
            cls.init()
        if cls._cfg is None:
            raise RuntimeError("MongoStore config not initialized")
        return cls.client()[cls._cfg.db_name][name.value]

    @classmethod
    def close(cls) -> None:
        if cls._client is not None:
            cls._client.close()
            cls._client = None


def get_jobs_collection() -> Collection:
    return MongoStore.collection(MongoDBCollections.JOBS)