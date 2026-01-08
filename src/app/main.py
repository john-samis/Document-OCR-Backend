""" Entry point for the fastapi application"""



import logging


from fastapi import FastAPI


from app.utilities.app_logger import AppLogger
from src.app.utilities.docx_tool import DocxTool



logging.basicConfig(level=logging.INFO)

# Alwasy remember it works via HTTP protocol methods
app = FastAPI()

@app.get("/")
def read_root():
    """ Root endpoint """

    return { "Hello": "World" }

@app.get("/tool")
def tool_endpoint():
    """ Tool endpoint """

    return { "Placholder: Tool "}