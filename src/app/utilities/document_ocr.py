""" Hold the OCR tool functions. """



from typing import Any, Sequence
from pathlib import Path
from dataclasses import dataclass

import easyocr


@dataclass(frozen=True)
class OCRArguments:
    languages: tuple[str, ...] = ("en",)
    gpu: bool = False

    min_confidence: float = 0.30  # min 30% on text
    detail: int = 1               
    paragraph: bool = False       
    decoder: str = "greedy"

    text_threshold: float = 0.7
    low_text: float = 0.4
    link_threshold: float = 0.4


class DocumentOCR:
    """ Contains helper functions for OCR processing. """

    def __init__(self, args: OCRArguments = OCRArguments()) -> None:
        self.args = args
        self.reader = easyocr.Reader(list(self.args.languages), gpu=self.args.gpu)


    def ocr_image(self, image_path: Path) -> list[dict[str, Any]]:
        """ Run OCR on one single image"""
        if image_path is None:
            raise ValueError("Image path is None")

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found at path: {image_path}")
        
        raw_read = self.reader.readtext(
            str(image_path),
            detail=self.args.detail,
            paragraph=self.args.paragraph,
            decoder=self.args.decoder,
            text_threshold=self.args.text_threshold,
            low_text=self.args.low_text,
            link_threshold=self.args.link_threshold,
        )

        blocks = self._normalize_easyocr_result(raw_read)
        blocks = self._filter_blocks(blocks, min_conf=self.args.min_confidence)
        blocks = self._sort_reading_order(blocks)
        return blocks
    
    def ocr_pages(self, image_paths: Sequence[Path]) -> dict[str, Any]:
        """
        OCR many page images. calls ocr_on_one_image() implicitly
        Returns a dict with per-page results + simple aggregate info.
        """
        pages: list[dict[str, Any]] = []
        total_blocks = 0

        for idx, p in enumerate(image_paths, start=1):
            blocks = self.ocr_image(p)
            total_blocks += len(blocks)
            pages.append(
                {
                    "page_index": idx,
                    "image_path": str(p),
                    "blocks": blocks,
                }
            )

        return {
            "page_count": len(image_paths),
            "total_blocks": total_blocks,
            "pages": pages,
        }
    
    def _normalize_easyocr_result(self, raw: list[Any]) -> list[dict[str, Any]]:
        """
        EasyOCR with detail=1 returns list of tuples:
        [ (bbox, text, conf), ... ]
        Normalize into dicts 
        """
        blocks: list[dict[str, Any]] = []

        for item in raw:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue

            bbox, text, conf = item[0], item[1], item[2]

            if not text:
                continue

            x_min, y_min, x_max, y_max = self._bbox_to_rect(bbox)
            blocks.append(
                {
                    "text": str(text).strip(),
                    "confidence": float(conf),
                    "bbox": bbox,
                    "x_min": x_min,
                    "y_min": y_min,
                    "x_max": x_max,
                    "y_max": y_max,
                    "cx": (x_min + x_max) / 2.0,
                    "cy": (y_min + y_max) / 2.0,
                    "w": (x_max - x_min),
                    "h": (y_max - y_min),
                }
            )

        return blocks

    @staticmethod
    def _filter_blocks(blocks: list[dict[str, Any]], min_conf: float) -> list[dict[str, Any]]:
        return [b for b in blocks if b.get("confidence", 0.0) >= min_conf and b.get("text")]

    @staticmethod
    def _sort_reading_order(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        MVP reading order: sort by line-ish (y) then x. Since we just get a grid there, it makes sense for the most part.
        To reduce random swaps within same line, bucket by y using a tolerance.
        """
        if not blocks:
            return blocks

        heights = sorted(b["h"] for b in blocks if b.get("h") is not None)
        median_h = heights[len(heights) // 2] if heights else 10.0
        y_tol = max(8.0, 0.6 * median_h)

        def key_fn(b: dict[str, Any]) -> tuple[int, float]:
            line_bucket = int(b["cy"] // y_tol)
            return line_bucket, b["cx"]

        return sorted(blocks, key=key_fn)

    @staticmethod
    def _bbox_to_rect(bbox: Any) -> tuple[float, float, float, float]:
        """
        Convert 4-point bbox into rectangle bounds.
        bbox is typically: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] as seen in the easyocr docs
        """
        try:
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            return float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))
        except Exception:
            # Fallback if bbox is weird, this caused issues previously.
            return 0.0, 0.0, 0.0, 0.0