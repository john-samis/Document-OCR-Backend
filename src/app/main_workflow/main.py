""" Main worflow for a ocr call"""




from src.app.utilities.docx_tool import DocxArguments, DocxTool
from src.app.utilities.pdf_intake import PDFIntake
from src.app.utilities.ocr_tool import DocumentOCR
from src.app.utilities.mongodb_atlas import MongoDBAccess


# pseudo coding the main routine hopefully


def start_ocr_job():

    # First create record in the mongo db 

    # pdf to jpeg


    # OCR with easy ocr, outputs coordinates, text, and confidence

    # Output into MathML

    # Output to docx



    pass




def main():
    pass


if __name__ == "__main__":
    main()