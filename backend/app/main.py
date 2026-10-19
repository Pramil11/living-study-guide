from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Living Study Guide API",
    description="AI-powered, source-linked study platform",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Welcome to Living Study Guide API",
        "status": "running"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Living Study Guide Backend"
    }