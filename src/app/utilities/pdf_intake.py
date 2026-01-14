""" Module to handle the initial pdf intake """


from pathlib import Path
from dataclasses import dataclass, field

from fastapi import UploadFile, HTTPException
from pdf2image import convert_from_path

from src.app.utilities.app_logger import AppLogger


@dataclass(frozen=True)
class PDFValidationConfig:
    max_pdf_size_bytes: int = field(default=25* 1024 * 1024)  # Should be 25 MB since it is directly uploaded to cloud run instance
    require_pdf_magic: bool = True

    def __post_init__(self):
        if self.max_pdf_size_bytes != (25 * 1024 * 1024) or not isinstance(int):
            raise RuntimeError(f"PDF Size Bytes Incorrect. {self.max_pdf_size_bytes} is not 25 MB")


class PDFIntake:
    """ Logic to intake a pdf"""

    def __init__(self, config: PDFValidationConfig = PDFValidationConfig) -> None:
        self.log = AppLogger.init_logger()
        self._cfg = config

    async def validate_save_upload(self, upload: UploadFile, job_dir: Path, filename: str ) -> Path:
        """ Validate the uploaded file is a PDF, and save it to {job_dir/filename}"""
        if upload is None:
            raise HTTPException(status_code=400, detail="Uploaded File Not Found")
        
        orig_name = upload.filename or ""
        if not orig_name.lower().endswith(".pdf"):
            raise HTTPException(status_code=415, detail="Only PDF files are supported for MVP.")

        if upload.content_type and upload.content_type.lower() not in ("application/pdf", "application/x-pdf"):
            # Some clients send weird values; keep this permissive if needed
            raise HTTPException(status_code=415, detail=f"Unexpected content type: {upload.content_type}")

        job_dir.mkdir(parents=True, exist_ok=True)
        out_path = job_dir / filename

        total = 0
        first_chunk = b""
        chunk_size = 1024 * 1024  # 1MB 

        try:
            await upload.seek(0)

            with out_path.open("wb") as f:
                while True:
                    chunk = await upload.read(chunk_size)
                    if not chunk:
                        break

                    if total == 0:
                        first_chunk = chunk[:16]

                    total += len(chunk)
                    if total > self.cfg.max_size_bytes:
                        try:
                            out_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large. Max is {self.cfg.max_size_bytes} bytes.",
                        )

                    f.write(chunk)

        finally:
            await upload.close()

        if self.cfg.require_pdf_magic and not first_chunk.startswith(b"%PDF-"):
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(status_code=415, detail="File is not a valid PDF (missing %PDF- header).")

        self.log.info(f"Saved PDF upload: {orig_name} -> {out_path} ({total} bytes)")
        return out_path

    def pdf_to_jpeg(
        self,
        pdf_file: Path,
        out_dir: Path,
        fmt: str = "jpeg",
        dpi: int = 250,
    ) -> list[Path]:
        """
        Convert PDF to images named page_1.jpg, page_2.jpg, and so on
        Returns a list of output image paths.
        """
        if pdf_file is None:
            raise RuntimeError("pdf_file is None")

        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_file}")

        out_dir.mkdir(parents=True, exist_ok=True)

        pages = convert_from_path(str(pdf_file), fmt=fmt.lower(), dpi=dpi)

        out_paths: list[Path] = []
        ext = "jpg" if fmt.lower() in ("jpg", "jpeg") else fmt.lower()

        for i, page in enumerate(pages, start=1):
            out_path = out_dir / f"page_{i}.{ext}"
            page.save(str(out_path), fmt.upper())
            out_paths.append(out_path)

        self.log.info(f"Converted {len(pages)} pages -> {out_dir}")
        return out_paths

