""" Small Math classifier for the ocr"""


import re

from typing import Any
from enum import Enum
from dataclasses import dataclass


class MathRE(Enum):
    # Can always add more to the regular expression if needed
    MATH_CHARS_RE = re.compile(r"[=+\-*/^_∑∫√≈≠≤≥∞πθλμΩαβγΔ→←↔]", re.UNICODE)
    MATH_WORDS_RE = re.compile(r"\b(sin|cos|tan|log|ln|lim|dx|dy|dz)\b", re.IGNORECASE)
    EQUATIONISH_RE = re.compile(r"\w\s*=\s*[\w(]")


@dataclass(frozen=True)
class MathPassConfig:
    min_math_signals: int = 1  # Could do better afterwards, but eh


class MathPass:
    """
    Math Pass tag blocks as math-like
    Later: replace with real math recognition -> OMML.
    """

    def __init__(self, cfg: MathPassConfig = MathPassConfig()) -> None:
        self.cfg = cfg

    def tag_blocks(self, ocr_result: dict[str, Any]) -> dict[str, Any]:
        """ Adds `is_math: bool` to each OCR block. For now still raw, but later feed into mathml"""
        out = dict(ocr_result)
        out_pages: list[dict[str, Any]] = []

        for page in ocr_result.get("pages", []):
            page_copy = dict(page)
            blocks_out: list[dict[str, Any]] = []

            for b in page.get("blocks", []):
                b2 = dict(b)
                text = b2.get("text", "") or ""
                b2["is_math"] = self._looks_like_math(text)
                blocks_out.append(b2)

            page_copy["blocks"] = blocks_out
            out_pages.append(page_copy)

        out["pages"] = out_pages
        return out

    def _looks_like_math(self, text: str) -> bool:
        signals = 0
        if MathRE.MATH_CHARS_RE.value.search(text):
            signals += 1
        if MathRE.MATH_WORDS_RE.value.search(text):
            signals += 1
        if MathRE.EQUATIONISH_RE.value.search(text):
            signals += 1

        sym_density = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if len(text) > 0 and (sym_density / max(1, len(text))) > 0.15:
            signals += 1

        return signals >= self.cfg.min_math_signals

