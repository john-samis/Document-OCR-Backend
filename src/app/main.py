""" Entry point for the fastapi application"""


import logging

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from src.app.utilities.app_logger import AppLogger
from src.app.utilities.pdf_intake import PDFIntake
from src.app.utilities.document_ocr import DocumentOCR, OCRArguments
from src.app.utilities.omml_pass import MathPass
from src.app.utilities.docx_tool import DocxTool

from src.app.utilities.mongodb_utils.job_store_util import MongoJobStore
from src.app.utilities.mongodb_utils.mongo_client import get_jobs_collection
from src.app.utilities.mongodb_utils.mongo_client import MongoStore

from src.app.main_workflow.job_status_enums import JobStatus, JobStep


# TODO: Package and encapsulate all of these setup/init calls
# TODO: Add more logging as logic is expanded
# Alwasy remember it works via HTTP protocol methods
# This stuff all works in an 'event-loop'. I need to actually understand what this is however.
# after any major changes, change gpu (like using a gpu on cloud compute)
logging.basicConfig(level=logging.INFO)
log = AppLogger.init_logger()
app = FastAPI()

# Mongo DB Init
jobs_col = get_jobs_collection()
job_store = MongoJobStore(jobs_col)

# Tools init
pdf_intake = PDFIntake()
math_pass = MathPass()
docx_tool = DocxTool()
ocr_engine = DocumentOCR(
    OCRArguments(
        languages=("en",),
        gpu=False,
        min_confidence=0.30,
        paragraph=False,
    )
)

BASE_TMP: Path = Path("/tmp/jobs")


@app.on_event("startup")
async def startup() -> None:
    await run_in_threadpool(job_store.ensure_indexes)
    log.info("MongoDB Indices Validated")
    log.info("Startup loop complete")

@app.on_event("shutdown")
async def shutdown() -> None:
    MongoStore.close()
    log.info("Mongo client closed.")
    log.info("Shutdown complete")

@app.get("/")
async def read_root():
    """ Root endpoint """
    return { "Root Endpoint": "ROOT OK" }


@app.post("/v1/jobs")
async def start_job():
    """ Create a Job doc and start the workflow, return the status, upload, and result urls"""

    # 1: Create a Job document in the mongo nosql databased
    # Include: settings, time created, expired, etc
    job_id = str(uuid4())
    settings = {"languages": ["en"], "min_confidence": 0.30}
    await run_in_threadpool(job_store.create_job, job_id, settings)

    result = {
        "job_id": job_id,
        "status_url":f"/v1/jobs/{job_id}",
        "upload_url":f"/v1/jobs/{job_id}/file",
        "result_url":f"/v1/jobs/{job_id}/result",
    }

    return result

@app.post("/v1/jobs/{job_id}/file")
async def job_handle_file(job_id: str, file: UploadFile = File(...)):
    """ 
    Main loop. Analyzes .pdf file, performs OCR, outputs DOCX
    
    
    """
    job = await run_in_threadpool(job_store.get_job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found, must create it first")

    job_dir = BASE_TMP/ job_id
    out_docx = job_dir / "result.docx"

    try:
        await run_in_threadpool(
            job_store.update_job,
            job_id,
            status=JobStatus.PROCESSING,
            step=JobStep.VALIDATE,
            progress=5
        )
        pdf_path = await pdf_intake.validate_save_upload(
            upload=file,
            job_dir=job_dir
        )
        pdf_size = pdf_path.stat().st_size

        await run_in_threadpool(
            job_store.update_job,
            job_id,
            status=JobStatus.UPLOADED,
            step=JobStep.VALIDATE,
            progress=15,
            input_update={
                "originalFilename": file.filename,
                "contentType": file.content_type,
                "sizeBytes": pdf_size,
                "pdfPath": str(pdf_path),
            },
        )

        await run_in_threadpool(
            job_store.update_job,
            job_id,
            status=JobStatus.PROCESSING,
            step=JobStep.CONVERT_PAGES,
            progress=20
        )

        images_dir = job_dir / "pages"
        image_paths = pdf_intake.pdf_to_jpeg(pdf_path, images_dir)

        await run_in_threadpool(
            job_store.update_job,
            job_id,
            step=JobStep.CONVERT_PAGES,
            progress=35,
            input_update={"imagesDir": str(images_dir), "pageCount": len(image_paths)},
        )

        await run_in_threadpool(
            job_store.update_job,
            job_id,
            step=JobStep.PROCESS_OCR,
            progress=40
        )

        ocr_result = await run_in_threadpool(ocr_engine.ocr_pages, image_paths)

        await run_in_threadpool(
            job_store.update_job,
            job_id,
            step=JobStep.PROCESS_OCR,
            progress=75,
            output_update={"totalBlocks": ocr_result.get("total_blocks", 0)},
        )

        ocr_tagged = await run_in_threadpool(math_pass.tag_blocks, ocr_result)

        await run_in_threadpool(
            job_store.update_job,
            job_id,
            step=JobStep.RENDER_DOCX,
            progress=85
        )

        await run_in_threadpool(
            docx_tool.render_document,
            ocr_tagged,
            out_docx
        )

        await run_in_threadpool(
            job_store.update_job,
            job_id,
            status=JobStatus.SUCCEEDED,
            step=JobStep.DONE,
            progress=100,
            output_update={"resultPath": str(out_docx)},
        )

        return {
            "job_id": job_id,
            "status": JobStatus.SUCCEEDED,
            "step": JobStep.DONE,
            "page_count": ocr_result["page_count"],
            "total_blocks": ocr_result["total_blocks"],
            "download_url": f"/v1/jobs/{job_id}/result",
        }

    except HTTPException as e:
        await run_in_threadpool(
            job_store.update_job,
            job_id,
            status=JobStatus.FAILED,
            step=JobStep.DONE,
            progress=100,
            error={"message": e.detail},
        )
        raise

    except Exception as e:
        await run_in_threadpool(
            job_store.update_job,
            job_id,
            status=JobStatus.FAILED,
            step=JobStep.DONE,
            progress=100,
            error={"message": str(e)},
        )
        raise HTTPException(status_code=500, detail="Processing failed.") from e

@app.get("/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get a job's status

    :param job_id: The unique job id.
    """
    document = await run_in_threadpool(job_store.get_job, job_id)
    if not document:
        raise HTTPException(status_code=404, detail="Job not found")

    return document

@app.get("/v1/jobs/{job_id}/result")
def get_job_result(job_id: str):
    job_dir = BASE_TMP / job_id
    out_docx = job_dir / "result.docx"

    if not out_docx.exists():
        raise HTTPException(status_code=404, detail="Result not found (job not finished or invalid job_id).")

    # This one si straight from the docs
    return FileResponse(
        path=str(out_docx),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{job_id}.docx",
    )

@app.get("/v1/smoke_test_backend")
def smoke_test_container():
    return { "Service": "Healthy"}

