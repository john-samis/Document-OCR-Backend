""" Entry point for the fastapi application"""


import logging

from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from src.app.utilities.pdf_intake import PDFIntake
from src.app.utilities.document_ocr import DocumentOCR, OCRArguments
from src.app.utilities.omml_pass import MathPass
from src.app.utilities.docx_tool import DocxTool

from src.app.main_workflow.job_status_enums import JobStatus, JobStep


# TODO: What should be async and what should be sync?
# Alwasy remember it works via HTTP protocol methods
# This stuff all works in an 'event-loop'. I need to actually understand what this is however.
# after any major changes, change gpu (like using a gpu on cloud compute)
logging.basicConfig(level=logging.INFO)
app = FastAPI()
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


@app.get("/")
def read_root():
    """ Root endpoint """

    return { "Root Enpoint": "Placeholder" }

@app.get("/tool")
def tool_endpoint():
    """ Tool endpoint """

    return { "Placholder: Tool "}



@app.post("/v1/jobs")
def start_job():
    """ Create a Job doc and start the workflow"""

    # 1: Create a Job document in the mongo nosql databased
    # Include: settingsm time created, expired

    pass




@app.post("/v1/jobs/{job_id}/file")
async def job_handle_file(job_id: str, file: UploadFile = File(...)):
    job_dir = Path("/tmp/jobs") / job_id
    pdf_path = await pdf_intake.validate_and_save_upload(file, job_dir)

    images_dir = job_dir / "pages"
    image_paths = pdf_intake.pdf_to_jpeg(pdf_path, images_dir)

    ocr_result = await run_in_threadpool(ocr_engine.ocr_pages, image_paths)

    # Math tagging pass (lightweight, but keep in threadpool for simplicity)
    ocr_tagged = await run_in_threadpool(math_pass.tag_blocks, ocr_result)

    # Render docx (sync) -> threadpool
    out_docx = job_dir / "result.docx"
    await run_in_threadpool(docx_tool.render_document, ocr_tagged, out_docx)

    return {
        "job_id": job_id,
        "status": JobStatus.SUCCEEDED,
        "step": JobStep.DOCX_RENDER,  # pick whatever enum name you have
        "page_count": ocr_result["page_count"],
        "total_blocks": ocr_result["total_blocks"],
        "pdf_path": str(pdf_path),
        "result_path": str(out_docx),
        "download_url": f"/v1/jobs/{job_id}/result",
    }

@app.get("/v1/jobs/{job_id}")
def get_job_status():
    """ Get the information of a job and whatnot. """

    # 1. Simply return metadata information
    # Include: status, progress, step, error, fileName, createdAt, expiresAt
    pass


@app.get("/v1/jobs/{job_id}/result")
def get_job_result(job_id: str):
    job_dir = Path("/tmp/jobs") / job_id
    out_docx = job_dir / "result.docx"

    if not out_docx.exists():
        raise HTTPException(status_code=404, detail="Result not found (job not finished or invalid job_id).")

    return FileResponse(
        path=str(out_docx),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{job_id}.docx",
    )



@app.get("/v1/smoke_test_backend")
def smoke_test_container():
    """ Check the health of the container. Will likely be better suited for integration tests."""
    return { "Service": "Healthy"}






