from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.pdf_processor import extract_pdf_pages

app = FastAPI(title="Living Study Guide API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    document_id = str(uuid4())
    file_path = UPLOAD_DIR / f"{document_id}.pdf"

    try:
        content = await file.read(MAX_FILE_SIZE + 1)

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(413, "PDF exceeds the 10 MB limit")

        if not content.startswith(b"%PDF-"):
            raise HTTPException(400, "Invalid PDF file")

        file_path.write_bytes(content)

        pages = extract_pdf_pages(str(file_path))

        return {
            "document_id": document_id,
            "filename": file.filename,
            "total_pages": len(pages),
            "pages": pages
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            422, "Unable to process this PDF"
        ) from exc
    finally:
        await file.close()
        file_path.unlink(missing_ok=True)