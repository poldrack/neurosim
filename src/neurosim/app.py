import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from neurosim.auth import check_passphrase, generate_token, validate_token
from neurosim.diagnosis import (
    build_llm_diagnosis_prompt,
    check_diagnosis,
    extract_diagnosis_tag,
    strip_diagnosis_tag,
)
from neurosim.disorders import get_random_disorder, load_disorders
from neurosim.llm_client import stream_chat
from neurosim.prompts import build_clinician_prompt, build_patient_prompt
from neurosim.session import SessionManager


class AuthRequest(BaseModel):
    passphrase: str


class StartRequest(BaseModel):
    role: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class DiagnoseRequest(BaseModel):
    session_id: str
    diagnosis: str


class RevealRequest(BaseModel):
    session_id: str


def create_app() -> FastAPI:
    load_dotenv()

    app = FastAPI(title="NeuroSim")

    project_root = Path(__file__).resolve().parent.parent.parent
    data_path = project_root / "data" / "disorder_taxonomy.json"
    static_path = project_root / "static"

    disorders = load_disorders(data_path)
    session_manager = SessionManager()

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and path not in ("/api/auth",):
            token = request.cookies.get("neurosim_token")
            if not validate_token(token):
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)

    @app.get("/api/auth/check")
    async def auth_check():
        return {"status": "ok"}

    @app.post("/api/auth")
    async def authenticate(req: AuthRequest, response: Response):
        if not check_passphrase(req.passphrase):
            return JSONResponse(status_code=401, content={"detail": "Invalid access code"})
        token = generate_token(req.passphrase)
        response.set_cookie(key="neurosim_token", value=token, httponly=True, samesite="strict")
        return {"status": "ok"}

    @app.post("/api/session/start")
    async def start_session(req: StartRequest):
        if req.role not in ("clinician", "patient"):
            return JSONResponse(status_code=400, content={"detail": "Role must be 'clinician' or 'patient'"})

        disorder = get_random_disorder(disorders)
        session = session_manager.create_session(role=req.role, disorder=disorder)

        disorder_info = None
        if req.role == "patient":
            disorder_info = disorder

        return {"session_id": session.session_id, "disorder_info": disorder_info}

    @app.post("/api/chat")
    async def chat(req: ChatRequest):
        session = session_manager.get_session(req.session_id)
        if not session:
            return JSONResponse(status_code=404, content={"detail": "Session not found"})
        if not session.active:
            return JSONResponse(status_code=400, content={"detail": "Session is no longer active"})

        session.add_message("user", req.message)

        if session.role == "clinician":
            system_prompt = build_patient_prompt(session.disorder)
        else:
            system_prompt = build_clinician_prompt()

        async def event_stream():
            full_response = ""
            async for token in stream_chat(session.messages, system_prompt):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            session.add_message("assistant", full_response)

            if session.role == "patient":
                diagnosed_name = extract_diagnosis_tag(full_response)
                if diagnosed_name:
                    is_correct = check_diagnosis(session.disorder["name"], diagnosed_name)
                    clean_text = strip_diagnosis_tag(full_response)
                    session.messages[-1]["content"] = clean_text
                    session_manager.deactivate_session(session.session_id)
                    feedback = _build_reveal_feedback(session.disorder)
                    yield f"data: {json.dumps({'done': True, 'diagnosis_proposed': True, 'correct': is_correct, 'diagnosed_as': diagnosed_name, 'disorder': session.disorder, 'feedback': feedback})}\n\n"
                    return

            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/api/diagnose")
    async def diagnose(req: DiagnoseRequest):
        session = session_manager.get_session(req.session_id)
        if not session:
            return JSONResponse(status_code=404, content={"detail": "Session not found"})
        if not session.active:
            return JSONResponse(status_code=400, content={"detail": "Session is no longer active"})

        is_correct = check_diagnosis(session.disorder["name"], req.diagnosis)

        if not is_correct:
            llm_prompt = build_llm_diagnosis_prompt(session.disorder["name"], req.diagnosis)
            llm_response = ""
            async for token in stream_chat(
                [{"role": "user", "content": llm_prompt}],
                "You are a medical terminology expert. Reply with exactly YES or NO.",
            ):
                llm_response += token
            if llm_response.strip().upper().startswith("YES"):
                is_correct = True

        if is_correct:
            session_manager.deactivate_session(session.session_id)
            return {
                "correct": True,
                "message": "Correct diagnosis!",
                "disorder": session.disorder,
            }
        else:
            return {
                "correct": False,
                "message": "Not quite. Keep investigating.",
            }

    @app.post("/api/reveal")
    async def reveal(req: RevealRequest):
        session = session_manager.get_session(req.session_id)
        if not session:
            return JSONResponse(status_code=404, content={"detail": "Session not found"})

        session_manager.deactivate_session(session.session_id)
        feedback = _build_reveal_feedback(session.disorder)
        return {"disorder": session.disorder, "feedback": feedback}

    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")

    return app


def _build_reveal_feedback(disorder: dict) -> str:
    """Build static feedback string from disorder details for reveal/diagnosis."""
    return (
        f"The disorder was {disorder['name']} (Category: {disorder.get('category', 'N/A')}). "
        f"Key symptoms include: {disorder['symptoms'][:200]}... "
        f"This is tested by: {disorder['how_to_test'][:200]}..."
    )


def main():
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
