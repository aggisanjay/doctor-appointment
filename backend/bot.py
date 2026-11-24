import asyncio
import os
import sys
from typing import Any, Dict

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, TextFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frameworks.rtvi import RTVIObserver, RTVIProcessor
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService, ElevenLabsSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from backend.tools import (
    ALL_TOOL_SCHEMAS,
    book_appointment_logic,
    cancel_appointment_logic,
    check_doctor_availability_logic,
    pipecat_book_appointment,
    pipecat_cancel_appointment,
    pipecat_check_doctor_availability,
)

SYSTEM_PROMPT = """You are Maya, the voice assistant for City Care Clinic.
You speak aloud to callers in a calm, professional, and friendly voice.

CRITICAL VOICE INSTRUCTIONS:
1. Speak in plain spoken English. Keep your spoken responses SHORT: at most 1 to 2 concise sentences.
2. NEVER use markdown, bullet points, numbered lists, asterisks, bold text, or emojis. Everything you write is spoken directly by text-to-speech.
3. For emergency or life-threatening symptoms, immediately tell the caller: "If this is a medical emergency, please hang up and call your local emergency services immediately." Never provide medical diagnoses or advice.
4. Never invent doctors, slots, or appointments. Only quote information directly returned from your tools.

WORKFLOW:
- Greet warmly: "Hello, thank you for calling City Care Clinic. How can I help you today?"
- To check availability: ask for the doctor name or speciality and preferred day. Call check_doctor_availability.
- When offering slots, mention only 2 to 3 available times so the caller is not overwhelmed.
- Once a slot is picked, collect the patient's name and 10-digit mobile number.
- MANDATORY CONFIRMATION RULE: You MUST read back the 10-digit phone number in grouped digits (for example: "I have your number as 9 8 7 6 5, 4 3 2 1 0. Is that correct?").
- Wait for the caller to explicitly say yes or confirm before calling book_appointment with phone_confirmed=True. If the caller says no or corrects a digit, update the number and read it back again.
- CANCELLATION WORKFLOW:
  * When a caller asks to cancel, DO NOT call cancel_appointment immediately.
  * First ask for their 10-digit mobile number if not already provided.
  * Once provided, READ BACK the 10-digit number and ask: "Is that correct?"
  * ONLY AFTER the caller says "yes" or confirms, call cancel_appointment with phone_confirmed=True.
  * If multiple active appointments are returned, read them out and ask which one to cancel.
- After any booking or cancellation tool call, immediately confirm the outcome in one sentence with the doctor's name, date, and time, and always ask: "Is there anything else I can help you with today?" to keep the conversation going.
"""


def build_pipeline_task(
    webrtc_connection: SmallWebRTCConnection,
    google_api_key: str,
    gemini_model: str,
    elevenlabs_api_key: str,
    elevenlabs_voice_id: str,
) -> tuple[PipelineTask, SmallWebRTCTransport, GoogleLLMService]:
    """Constructs the complete Pipecat voice pipeline."""

    # 1. WebRTC Transport with Silero VAD (tuned to avoid speaker feedback interruptions)
    from pipecat.audio.vad.vad_analyzer import VADParams

    vad_analyzer = SileroVADAnalyzer(
        params=VADParams(
            confidence=0.8,
            start_secs=0.45,
            stop_secs=0.5,
            min_volume=0.5,
        )
    )
    transport_params = TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        camera_in_enabled=False,
        vad_enabled=True,
        vad_analyzer=vad_analyzer,
        vad_audio_passthrough=True,
    )
    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=transport_params,
    )

    # 2. ElevenLabs STT with server-side VAD segmentation and strict English language locking
    from pipecat.services.elevenlabs.stt import CommitStrategy

    clinic_keyterms = [
        "Dr. Sharma",
        "Dr. Patel",
        "Dr. Mehta",
        "Dr. Rao",
        "Dr. Iyer",
        "Dr. Gupta",
        "Dr. Desai",
        "Cardiology",
        "Dermatology",
        "Pediatrics",
        "Orthopedics",
        "General Medicine",
        "appointment",
        "booking",
        "cancel",
        "reschedule",
        "confirm",
        "yes",
        "no",
    ]

    try:
        stt = ElevenLabsRealtimeSTTService(
            api_key=elevenlabs_api_key,
            commit_strategy=CommitStrategy.VAD,
            settings=ElevenLabsRealtimeSTTService.Settings(
                language="en",
                keyterms=clinic_keyterms,
                vad_silence_threshold_secs=0.9,
                vad_threshold=0.4,
                filter_background_audio=True,
            ),
        )
    except Exception as e:
        logger.warning(f"Falling back to standard ElevenLabsSTTService: {e}")
        stt = ElevenLabsSTTService(
            api_key=elevenlabs_api_key,
            settings=ElevenLabsSTTService.Settings(
                language="en",
            ),
        )

    # 3. Google Gemini LLM Service (fast minimal-thinking for voice agents)
    llm = GoogleLLMService(
        api_key=google_api_key,
        settings=GoogleLLMService.Settings(
            model=gemini_model or "gemini-3.5-flash-lite",
            system_instruction=SYSTEM_PROMPT,
            thinking=GoogleLLMService.ThinkingConfig(thinking_level="minimal"),
        ),
    )

    # 4. ElevenLabs TTS (Sarah - clear, natural healthcare voice)
    tts = ElevenLabsTTSService(
        api_key=elevenlabs_api_key,
        settings=ElevenLabsTTSService.Settings(
            voice=elevenlabs_voice_id or "EXAVITQu4vr4xnSDxMaL",
        ),
    )

    # 5. RTVI Processor & Observer for real-time browser transcripts
    rtvi = RTVIProcessor()
    rtvi_observer = RTVIObserver(rtvi=rtvi)

    # 6. Context Aggregators
    from pipecat.processors.aggregators.llm_context import LLMContext

    context = LLMContext(
        messages=[],
        tools=ALL_TOOL_SCHEMAS,
    )
    context_pair = LLMContextAggregatorPair(context)

    # 7. Pipeline:
    # transport.input -> RTVI -> STT -> user context aggregator -> LLM -> TTS -> transport.output -> assistant context aggregator
    pipeline = Pipeline([
        transport.input(),
        rtvi,
        stt,
        context_pair.user(),
        llm,
        tts,
        transport.output(),
        context_pair.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
        ),
        observers=[rtvi_observer],
        enable_rtvi=True,
        rtvi_processor=rtvi,
    )

    return task, transport, llm


async def run_bot_pipeline(
    webrtc_connection: SmallWebRTCConnection,
    google_api_key: str,
    gemini_model: str,
    elevenlabs_api_key: str,
    elevenlabs_voice_id: str,
):
    """Runs the voice bot pipeline for a WebRTC session."""
    logger.info("Initializing Pipecat voice pipeline...")
    task, transport, llm = build_pipeline_task(
        webrtc_connection=webrtc_connection,
        google_api_key=google_api_key,
        gemini_model=gemini_model,
        elevenlabs_api_key=elevenlabs_api_key,
        elevenlabs_voice_id=elevenlabs_voice_id,
    )

    runner = PipelineRunner()

    greeting_sent = False

    async def speak_greeting():
        nonlocal greeting_sent
        if greeting_sent:
            return
        greeting_sent = True
        # Short delay to ensure audio track negotiation is completely settled
        await asyncio.sleep(0.6)
        logger.info("Triggering Maya's spoken greeting via ElevenLabs TTS...")
        greeting = "Hello, thank you for calling City Care Clinic. How can I help you today?"
        await task.queue_frame(TTSSpeakFrame(text=greeting))

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected: {client}. Queueing clinic greeting.")
        asyncio.create_task(speak_greeting())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected: {client}. Cancelling pipeline task.")
        await task.cancel()

    try:
        await runner.run(task)
    except asyncio.CancelledError:
        logger.info("Pipeline task cancelled cleanly.")
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
    finally:
        logger.info("Pipeline finished.")
