""" Module to contain the job status enums"""


from dataclasses import dataclass
from enum import Enum, auto, StrEnum


class JobStatus(StrEnum):
    CREATED = "CREATED"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class JobStep(StrEnum):
    VALIDATE = "VALIDATE"
    CONVERT_PAGES = "CONVERT_PAGES"
    PROCESS_OCR = "PROCESS_OCR"
    RENDER_DOCX = "RENDER_DOCX"
    DONE = "DONE"


@dataclass
class MongoDocumentSchema:
    _id: str
    status: str
    step: str
    progress: str
    error: dict
    settings: dict
    input: dict
    output: dict