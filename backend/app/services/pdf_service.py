from dataclasses import dataclass
import pymupdf as fitz


@dataclass(frozen=True)
class Chunk:
    document: str
    page: int
    text: str


def extract_chunks(data: bytes, filename: str, chunk_size: int = 1100, overlap: int = 180) -> list[Chunk]:
    """Chunk within individual pages so every passage retains its exact page."""
    try:
        pdf = fitz.open(stream=data, filetype="pdf")
        if pdf.needs_pass:
            raise ValueError("Password-protected PDFs are not supported.")
        chunks = []
        for page_number, page in enumerate(pdf, 1):
            text = " ".join(page.get_text().split())
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                if end < len(text):
                    boundary = text.rfind(" ", start + chunk_size // 2, end)
                    if boundary > start:
                        end = boundary
                passage = text[start:end].strip()
                if passage:
                    chunks.append(Chunk(filename, page_number, passage))
                if end == len(text):
                    break
                start = max(start + 1, end - overlap)
        pdf.close()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Could not read this PDF.") from exc
    if not chunks:
        raise ValueError("Could not extract text from this PDF. Scanned PDFs need OCR.")
    return chunks
