
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from openai import (
    APIConnectionError,
    APITimeoutError,
    APIStatusError
)

from app.pdf_processor import extract_pdf_pages
from app.ai_service import generate_summary, MODEL_NAME


# --------------------------------------------------
# FastAPI Application
# --------------------------------------------------

app = FastAPI(
    title="Living Study Guide API",
    description=(
        "AI-powered study guide generation with "
        "source-linked learning materials."
    ),
    version="0.3.0"
)


# --------------------------------------------------
# CORS Configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# File Configuration
# --------------------------------------------------

UPLOAD_DIR = (
    Path(__file__).resolve().parent.parent / "uploads"
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024

# Limit text sent to the AI for this MVP.
# Later we will implement document chunking and RAG.
MAX_SOURCE_CHARS = 18000


# --------------------------------------------------
# Root Endpoint
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "application": "Living Study Guide",
        "version": "0.3.0",
        "status": "running",
        "ai_provider": "MindRouter",
        "model": MODEL_NAME
    }


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Living Study Guide Backend",
        "ai_provider": "MindRouter",
        "model": MODEL_NAME
    }


# --------------------------------------------------
# PDF Processing Helper
# --------------------------------------------------

async def process_pdf(file: UploadFile):

    if (
        not file.filename
        or not file.filename.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    document_id = str(uuid4())

    file_path = UPLOAD_DIR / f"{document_id}.pdf"

    try:
        content = await file.read(MAX_FILE_SIZE + 1)

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="PDF exceeds the 10 MB limit."
            )

        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file."
            )

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
            status_code=422,
            detail="Unable to process this PDF."
        ) from exc

    finally:
        await file.close()
        file_path.unlink(missing_ok=True)


# --------------------------------------------------
# PDF Upload and Text Extraction
# --------------------------------------------------

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...)
):

    result = await process_pdf(file)

    return result


# --------------------------------------------------
# Prepare Text for AI
# --------------------------------------------------

def prepare_source_pages(pages: list[dict]):

    selected_pages = []

    remaining_characters = MAX_SOURCE_CHARS

    truncated = False

    nonempty_pages = [
        page for page in pages
        if page["text"].strip()
    ]

    for page in nonempty_pages:

        if remaining_characters <= 0:
            truncated = True
            break

        text = page["text"]

        selected_text = text[:remaining_characters]

        selected_pages.append({
            "page_number": page["page_number"],
            "text": selected_text
        })

        remaining_characters -= len(selected_text)

        if len(selected_text) < len(text):
            truncated = True
            break

    return selected_pages, truncated


# --------------------------------------------------
# AI Study Guide Generation
# --------------------------------------------------

@app.post("/api/study/generate")
async def create_study_guide(
    file: UploadFile = File(...)
):

    # Step 1: Extract PDF text
    document = await process_pdf(file)

    pages = document["pages"]

    # Step 2: Check whether text exists
    if not any(page["text"].strip() for page in pages):
        raise HTTPException(
            status_code=422,
            detail=(
                "No extractable text found. "
                "Scanned PDFs may require OCR."
            )
        )

    # Step 3: Prepare source content
    selected_pages, truncated = prepare_source_pages(
        pages
    )

    # Step 4: Generate AI summary
    try:
        summary = await generate_summary(
            selected_pages
        )

    except APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="MindRouter request timed out."
        )

    except APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to MindRouter."
        )

    except APIStatusError as exc:

        if exc.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail=(
                    "MindRouter rate limit or token "
                    "quota exceeded. Try again later."
                )
            )

        raise HTTPException(
            status_code=502,
            detail=(
                f"MindRouter returned an error "
                f"(HTTP {exc.status_code})."
            )
        )

    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=502,
            detail="AI generation failed."
        ) from exc

    # Step 5: Return generated study guide
    return {
        "document_id": document["document_id"],
        "filename": document["filename"],
        "total_pages": document["total_pages"],

        "ai_provider": "MindRouter",
        "model": MODEL_NAME,

        "summary": summary,

        "source_pages": [
            page["page_number"]
            for page in selected_pages
        ],

        "source_characters": sum(
            len(page["text"])
            for page in selected_pages
        ),

        "partial_document": truncated,

        "verification_status": "not_verified"
    }
