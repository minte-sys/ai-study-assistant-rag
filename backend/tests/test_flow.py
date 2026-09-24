"""Offline integration check for extraction, retrieval, endpoints and page metadata."""
import asyncio
from unittest.mock import patch
import pymupdf as fitz
import httpx
from app.main import app


def pdf_bytes():
    doc = fitz.open()
    for content in ("Virtual memory extends available memory using storage.", "A cache stores recently used data for faster access."):
        page = doc.new_page()
        page.insert_text((40, 40), content)
    data = doc.tobytes()
    doc.close()
    return data


async def mock_embed(texts):
    return [[1.0, 0.0] if "virtual" in text.lower() else [0.0, 1.0] for text in texts]


async def mock_answer(question, passages):
    assert passages[0].startswith("[lecture.pdf, page 1]")
    return "Virtual memory extends available memory using storage."


async def run():
    transport = httpx.ASGITransport(app=app)
    with patch("app.main.embed", side_effect=mock_embed), patch("app.main.answer", side_effect=mock_answer):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/health")).json() == {"status": "ok"}
            invalid = await client.post("/upload", files={"file": ("wrong.txt", b"no", "text/plain")})
            assert invalid.status_code == 400
            uploaded = await client.post("/upload", files={"file": ("lecture.pdf", pdf_bytes(), "application/pdf")})
            assert uploaded.status_code == 200, uploaded.text
            assert uploaded.json()["pages"] == 2
            result = await client.post("/ask", json={"question": "What is virtual memory?"})
            assert result.status_code == 200, result.text
            assert result.json()["sources"][0] == {"document": "lecture.pdf", "page": 1}
            print("PASS: health, invalid upload, two-page extraction, embedding/retrieval, answer, page reference")


if __name__ == "__main__":
    asyncio.run(run())
