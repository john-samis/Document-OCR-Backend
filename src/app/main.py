""" Entry point for the fastapi application"""


import logging


from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
# TODO: What should be async and what should be sync?
# Alwasy remember it works via HTTP protocol methods
app = FastAPI()

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
def job_handle_file():
    """ Handle the file upload process. """
    # 1) Handles Upload  , validation checks (only user input for the most part)
    # 2) Run main workflow loop, pdf -> jpg, ocr -> text + math OMML -> docx

    # 3) Return the download at the get endpoint








@app.get("/v1/jobs/{job_id}")
def get_job_status():
    """ Get the information of a job and whatnot. """

    # 1. Simply return metadata information
    # Include: status, progress, step, error, fileName, createdAt, expiresAt
    pass


app.get("/v1/jobs/{job_id}/result")
def get_job_result():
    """ Should """
    # TODO: Should definitely implicitly call get_job_status

    # 1) Return the byte stream of the output document



app.get("/v1/smoke_test_backend")
def smoke_test_container():
    """ Check the health of the container. Will likely be better suited for integration tests."""
    return { "Service": "Healthy"}






