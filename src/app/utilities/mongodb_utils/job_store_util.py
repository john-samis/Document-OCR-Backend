""" Wrapper for storing jobs to db"""


from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from pymongo.collection import Collection

from src.app.main_workflow.job_status_enums import JobStatus, JobStep


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MongoJobStore:
    jobs: Collection
    default_ttl_hours: int = 24

    def ensure_indexes(self) -> None:
        self.jobs.create_index("expiresAt", expireAfterSeconds=0)
        self.jobs.create_index("createdAt")

    def create_job(self, job_id: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        now = utcnow()
        doc = {
            "_id": job_id,
            "status": JobStatus.CREATED.value,
            "step": JobStep.VALIDATE.value,
            "progress": 0,
            "createdAt": now,
            "updatedAt": now,
            "expiresAt": now + timedelta(hours=self.default_ttl_hours),
            "error": {},
            "settings": settings or {},
            "input": {},
            "output": {},
        }
        self.jobs.insert_one(doc)
        return doc

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.find_one({"_id": job_id})

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[JobStatus] = None,
        step: Optional[JobStep] = None,
        progress: Optional[int] = None,
        error: Optional[Dict[str, Any]] = None,
        input_update: Optional[Dict[str, Any]] = None,
        output_update: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        update: Dict[str, Any] = {"$set": {"updatedAt": utcnow()}}
        set_fields: Dict[str, Any] = {}

        if status is not None:
            set_fields["status"] = status.value
        if step is not None:
            set_fields["step"] = step.value
        if progress is not None:
            set_fields["progress"] = int(progress)
        if error is not None:
            set_fields["error"] = error

        if set_fields:
            update["$set"].update(set_fields)

        if input_update:
            update.setdefault("$set", {})
            for k, v in input_update.items():
                update["$set"][f"input.{k}"] = v

        if output_update:
            update.setdefault("$set", {})
            for k, v in output_update.items():
                update["$set"][f"output.{k}"] = v

        self.jobs.update_one({"_id": job_id}, update)
        doc = self.get_job(job_id)
        if doc is None:
            raise KeyError(f"Job not found: {job_id}")
        return doc
