import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCPatchRequest,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)

from backend.bot import run_bot_pipeline
from backend.events import broadcaster
from backend.store import store
from backend.tools import (
    book_appointment_logic,
    cancel_appointment_logic,
    check_doctor_availability_logic,
)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

webrtc_handler = SmallWebRTCRequestHandler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Doctor Appointment Assistant backend...")
    loop = asyncio.get_running_loop()
    broadcaster.set_loop(loop)
    yield
    logger.info("Shutting down backend...")
    await webrtc_handler.close()


app = FastAPI(
    title="Doctor Appointment Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "gemini_model": GEMINI_MODEL,
        "has_google_key": bool(GOOGLE_API_KEY and not GOOGLE_API_KEY.startswith("your_")),
        "has_elevenlabs_key": bool(ELEVENLABS_API_KEY and not ELEVENLABS_API_KEY.startswith("your_")),
    }


@app.get("/api/doctors")
async def get_doctors():
    """Get all doctors with their availability and free slots grouped by date."""
    return store.get_doctors_overview()


@app.get("/api/appointments")
async def get_appointments():
    """Get all booked and cancelled appointments."""
    return store.get_all_appointments()


@app.post("/api/test/action")
async def test_action(request: Request):
    """
    Test endpoint allowing curl / automated verification to drive tool actions
    and verify live SSE emissions without audio pipeline.
    """
    data = await request.json()
    action = data.get("action")
    params = data.get("params", {})

    if action == "check_doctor_availability":
        result = check_doctor_availability_logic(
            doctor_name=params.get("doctor_name"),
            speciality=params.get("speciality"),
            date=params.get("date"),
        )
        return JSONResponse(content=result)
    elif action == "book_appointment":
        result = book_appointment_logic(
            doctor_id=params.get("doctor_id", ""),
            slot_id=params.get("slot_id", ""),
            patient_name=params.get("patient_name", ""),
            phone_number=params.get("phone_number", ""),
            phone_confirmed=bool(params.get("phone_confirmed", False)),
        )
        return JSONResponse(content=result)
    elif action == "cancel_appointment":
        result = cancel_appointment_logic(
            phone_number=params.get("phone_number", ""),
            phone_confirmed=bool(params.get("phone_confirmed", False)),
            appointment_id=params.get("appointment_id"),
        )
        return JSONResponse(content=result)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@app.get("/api/events")
async def sse_events(request: Request):
    """Server-Sent Events endpoint to stream real-time updates to the dashboard."""
    queue = broadcaster.subscribe()

    async def event_generator():
        try:
            # Send initial ping event
            yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                try:
                    # Wait for message with timeout to allow periodic disconnect checks
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: message\ndata: {message}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat comment
                    yield ": keep-alive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/offer")
async def handle_offer(request: SmallWebRTCRequest):
    """WebRTC offer endpoint: negotiates SDP and kicks off Pipecat pipeline."""
    # Check credentials
    g_key = os.getenv("GOOGLE_API_KEY", GOOGLE_API_KEY)
    e_key = os.getenv("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY)
    v_id = os.getenv("ELEVENLABS_VOICE_ID") or ELEVENLABS_VOICE_ID or "EXAVITQu4vr4xnSDxMaL"
    model = os.getenv("GEMINI_MODEL") or GEMINI_MODEL or "gemini-3.5-flash-lite"

    if not g_key or g_key.startswith("your_"):
        logger.warning("GOOGLE_API_KEY is not configured with a valid key.")
    if not e_key or e_key.startswith("your_"):
        logger.warning("ELEVENLABS_API_KEY is not configured with a valid key.")

    async def webrtc_connection_callback(connection):
        logger.info(f"WebRTC connection established for peer {connection.pc_id}. Starting Pipecat voice pipeline...")
        # Start pipeline in the background so request handler can return SDP answer immediately
        asyncio.create_task(
            run_bot_pipeline(
                webrtc_connection=connection,
                google_api_key=g_key,
                gemini_model=model,
                elevenlabs_api_key=e_key,
                elevenlabs_voice_id=v_id,
            )
        )

    try:
        answer = await webrtc_handler.handle_web_request(
            request=request,
            webrtc_connection_callback=webrtc_connection_callback,
        )
        return JSONResponse(content=answer)
    except Exception as e:
        logger.error(f"Error handling WebRTC offer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/offer")
async def handle_patch(request: SmallWebRTCPatchRequest):
    """WebRTC ICE candidates patch endpoint."""
    try:
        await webrtc_handler.handle_patch_request(request)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error handling ICE candidate patch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Serve built frontend in production if dist/ exists
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist_path):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
