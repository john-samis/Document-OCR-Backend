""" Store the dataclasses for the metadata collected during an ocr process"""

from dataclasses import dataclass


@dataclass
class MetaData:
    job_id: str
    status: str
    progress: str
    step: str
    error: str
    file_name: str
    created_at: str
    expires_at: str

