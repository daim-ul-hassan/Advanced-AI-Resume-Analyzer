from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.models import AnalysisRequest, ResumeUploadResponse, SessionPayload, VectorBuildResponse
from app.services.activity import get_activity, log_activity
from app.services.parser import ALLOWED_SUFFIXES, extract_resume_text
from app.services.rag import analyze_resume, build_vector_payload
from app.services.storage import (
    ROOT_DIR,
    create_or_authenticate_user,
    delete_user_profile,
    ensure_dirs,
    get_user_upload_dir,
    load_profile,
    load_state,
    load_vector_base,
    save_state,
    save_vector_base,
)


ensure_dirs()

app = FastAPI(title="AI Resume Analyzer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "resume-analyzer-dev-secret"),
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 24 * 365,
)

app.mount("/static", StaticFiles(directory=ROOT_DIR / "app" / "static"), name="static")


def _require_user_id(request: Request) -> str:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Please log in first.")
    return str(user_id)


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(ROOT_DIR / "app" / "static" / "index.html")


@app.get("/api/bootstrap")
def bootstrap(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        return {
            "authenticated": False,
            "profile": {"name": "", "theme": "dark-ai"},
            "state": {
                "resume_filename": "",
                "vector_ready": False,
                "job_description": "",
                "last_analysis": None,
            },
            "activity": [],
        }

    state = load_state(str(user_id))
    return {
        "authenticated": True,
        "profile": load_profile(str(user_id)),
        "state": {
            "resume_filename": state.get("resume_filename", ""),
            "vector_ready": state.get("vector_ready", False),
            "job_description": state.get("job_description", ""),
            "last_analysis": state.get("last_analysis"),
        },
        "activity": [entry.model_dump() for entry in get_activity(str(user_id))],
    }


@app.post("/api/session")
def create_session(payload: SessionPayload, request: Request) -> dict:
    try:
        user_id, created = create_or_authenticate_user(
            payload.name,
            payload.password,
            payload.theme,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    request.session["user_id"] = user_id
    request.session["user_name"] = payload.name.strip()
    log_activity(
        user_id,
        "Session started",
        "Created a new workspace session." if created else "Logged back into the saved workspace.",
    )
    return {"message": "Session started successfully.", "created": created}


@app.post("/api/logout")
def logout(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if user_id:
        log_activity(str(user_id), "Logged out", "Ended the current workspace session.")
    request.session.clear()
    return {"message": "Logged out successfully."}


@app.post("/api/revoke-profile")
def revoke_profile(request: Request) -> dict:
    user_id = _require_user_id(request)
    log_activity(user_id, "Profile revoked", "Deleted the current profile and all saved workspace data.")
    delete_user_profile(user_id)
    request.session.clear()
    return {"message": "Profile deleted successfully."}


@app.post("/api/upload", response_model=ResumeUploadResponse)
async def upload_resume(request: Request, file: UploadFile = File(...)) -> ResumeUploadResponse:
    user_id = _require_user_id(request)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported.")

    original_name = Path(file.filename or "resume.txt").name
    destination = get_user_upload_dir(user_id) / original_name
    content = await file.read()
    destination.write_bytes(content)

    resume_text = extract_resume_text(destination)
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="The uploaded file did not contain readable text.")

    state = load_state(user_id)
    state.update(
        {
            "resume_filename": destination.name,
            "resume_path": str(destination),
            "resume_text": resume_text,
            "vector_ready": False,
            "last_analysis": None,
        }
    )
    save_state(user_id, state)
    save_vector_base(user_id, {"chunks": []})
    log_activity(user_id, "Resume uploaded", f"Saved '{destination.name}' and extracted {len(resume_text)} characters.")

    return ResumeUploadResponse(
        filename=destination.name,
        saved_path=str(destination),
        characters=len(resume_text),
        message="Resume saved and parsed successfully.",
    )


@app.post("/api/vectorize", response_model=VectorBuildResponse)
def build_vector_base_endpoint(request: Request) -> VectorBuildResponse:
    user_id = _require_user_id(request)
    state = load_state(user_id)
    resume_text = state.get("resume_text", "")
    if not resume_text:
        raise HTTPException(status_code=400, detail="Upload a resume before building the vector base.")

    vector_payload = build_vector_payload(resume_text)
    save_vector_base(user_id, vector_payload)
    state["vector_ready"] = True
    state["last_analysis"] = None
    save_state(user_id, state)
    log_activity(user_id, "Vector base built", f"Created {len(vector_payload['chunks'])} searchable resume chunks.")

    return VectorBuildResponse(
        chunk_count=len(vector_payload["chunks"]),
        message="Vector base built successfully.",
    )


@app.post("/api/analyze")
def analyze_resume_endpoint(payload: AnalysisRequest, request: Request) -> dict:
    user_id = _require_user_id(request)
    state = load_state(user_id)
    vector_payload = load_vector_base(user_id)
    resume_text = state.get("resume_text", "")
    if not resume_text:
        raise HTTPException(status_code=400, detail="Upload a resume first.")
    if not vector_payload.get("chunks"):
        raise HTTPException(status_code=400, detail="Build the vector base before launching analysis.")

    log_activity(user_id, "Analysis started", f"Started analysis with provider '{payload.provider}'.")
    result = analyze_resume(
        resume_text=resume_text,
        vector_payload=vector_payload,
        job_description=payload.job_description,
        provider=payload.provider,
        gemini_key=(payload.gemini_key or "").strip() or None,
        groq_key=(payload.groq_key or "").strip() or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    )

    state["job_description"] = payload.job_description
    state["last_analysis"] = result
    save_state(user_id, state)
    log_activity(user_id, "Analysis finished", f"Analysis completed with score {result['score']} using {result['provider_used']}.")
    return result


@app.get("/api/activity")
def activity_endpoint(request: Request) -> dict:
    user_id = _require_user_id(request)
    return {"activity": [entry.model_dump() for entry in get_activity(user_id)]}
