"""Safe extraction of meeting notes from uploaded documents."""
import io

from fastapi import HTTPException

ALLOWED = {".txt", ".md", ".docx", ".pdf"}
MAX_CHARS = 60000


def extract_text(filename: str, data: bytes, max_mb: int) -> str:
    name = (filename or "").lower()
    ext = name[name.rfind(".") :] if "." in name else ""
    if ext not in ALLOWED:
        raise HTTPException(415, f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED))}")
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"File too large (limit {max_mb} MB)")
    try:
        if ext in {".txt", ".md"}:
            text = data.decode("utf-8", errors="replace")
        elif ext == ".docx":
            from docx import Document

            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages[:50])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, f"Could not read document: {e}") from e
    text = text.replace("\x00", "").strip()
    if not text:
        raise HTTPException(422, "No readable text found in the document")
    return text[:MAX_CHARS]
