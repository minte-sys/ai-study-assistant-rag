import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .services.ai_service import AIServiceError, answer, embed
from .services.pdf_service import extract_chunks
from .services.retrieval_service import DocumentIndex

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app = FastAPI(title="AI Study Assistant")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")], allow_methods=["GET", "POST"], allow_headers=["*"])
index: DocumentIndex | None = None
lock = asyncio.Lock()
MAX_BYTES = 15 * 1024 * 1024


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    global index
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file.")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "PDF must be smaller than 15 MB.")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "Please upload a valid PDF file.")
    filename = Path(file.filename.replace("\\", "/")).name
    async with lock:
        try:
            chunks = extract_chunks(data, filename)
            vectors = []
            for start in range(0, len(chunks), 64):
                vectors.extend(await embed([chunk.text for chunk in chunks[start:start + 64]]))
            new_index = DocumentIndex(chunks, vectors)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except AIServiceError as exc:
            raise HTTPException(503, str(exc)) from exc
        index = new_index  # Preserve the previous document if processing fails.
    return {"document": filename, "pages": len({c.page for c in chunks}), "chunks": len(chunks)}


@app.post("/ask")
async def ask(request: Question):
    async with lock:
        if index is None:
            raise HTTPException(400, "Please upload a document first.")
        try:
            vector = (await embed([request.question]))[0]
            chunks = index.search(vector)
            passages = [f"[{chunk.document}, page {chunk.page}] {chunk.text}" for chunk in chunks]
            response = await answer(request.question, passages)
        except AIServiceError as exc:
            raise HTTPException(503, str(exc)) from exc
        except (ValueError, IndexError) as exc:
            raise HTTPException(503, "Unable to search this document.") from exc
        sources = [] if response == "I could not find that in the document." else list(dict.fromkeys((chunk.document, chunk.page) for chunk in chunks))
        return {"answer": response, "sources": [{"document": doc, "page": page} for doc, page in sources]}
