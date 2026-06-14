import re
import tempfile
import unicodedata
from pathlib import Path

import fitz


def read_pdf(source: bytes | str | Path) -> tuple[str, int]:
    if isinstance(source, bytes):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(source)
            tmp.flush()
            return _read_pdf_path(Path(tmp.name))
    return _read_pdf_path(Path(source))


def _read_pdf_path(path: Path) -> tuple[str, int]:
    with fitz.open(path) as pdf:
        pages = [page.get_text("text") or "" for page in pdf]
    text = "\n\n".join(pages)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise ValueError("No extractable text found in PDF. The file may be scanned.")
    return text, len(pages)
