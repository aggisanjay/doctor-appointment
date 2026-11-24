# City Care Clinic — Voice-Based Doctor Appointment Assistant

A real-time, voice-driven doctor appointment scheduling assistant. Callers speak naturally in the browser to an AI receptionist ("Maya") to check doctor schedules, book appointments, and cancel existing bookings.

The agent identifies callers solely by the 10-digit mobile number they speak aloud (no OTP, no login, no caller ID). The agent must read back the number digit-by-digit and obtain explicit confirmation ("yes") before any booking or cancellation is executed. A companion web dashboard displays live transcripts, doctor availability across 5 days, and real-time appointments synchronized via Server-Sent Events (SSE).

---

## Technology Stack

- **Audio Pipeline**: [Pipecat AI](https://github.com/pipecat-ai/pipecat) (v1.17.0) with WebRTC (`SmallWebRTCTransport`) and Silero VAD.
- **Speech-to-Text (STT)**: ElevenLabs STT (`ElevenLabsRealtimeSTTService` / `ElevenLabsSTTService`).
- **Text-to-Speech (TTS)**: ElevenLabs TTS (`ElevenLabsTTSService`, streaming PCM audio frames).
- **LLM**: **Google Gemini 2.5 Flash** (`gemini-2.5-flash`, Google AI Studio free tier quota). Configurable via `GEMINI_MODEL` environment variable.
- **Backend**: FastAPI + Uvicorn + Pydantic (async Python 3.12).
- **Frontend**: React 19 + Vite + TypeScript with custom CSS clinic design system (no generic AI look).

---

## Key Features

1. **Voice Pipeline**:
   `caller audio -> WebRTC -> Silero VAD -> ElevenLabs STT -> user context aggregator -> Gemini 2.5 Flash -> ElevenLabs TTS -> WebRTC output -> assistant context aggregator`.
2. **Mandatory Confirmation & Security Enforced In Code**:
   - Rejects booking or cancellation in Python if `phone_confirmed=False` (not just prompt instructions).
   - Normalizes spoken Indian mobile numbers: handles "+91", leading "0", word digits ("nine eight seven..."), multipliers ("double nine"), requiring exactly 10 digits starting with 6, 7, 8, or 9.
   - Enforces slot locks: prevents double-booking a slot, or a patient booking the same doctor twice at the same time.
   - Restores cancelled slots back to availability immediately.
   - Requires disambiguation if a caller has multiple active appointments.
3. **Phone-Style Call Screen**:
   - Realistic mobile modal: Ringing (synthesized dual-tone PBX ringback) -> Connected (live timer, mute mic toggle, live waveform) -> Ended (synthesized 3-pulse disconnect tone).
   - In-phone live transcript stream and slide-in confirmation/cancellation cards.
4. **Clinic Identity Design System**:
   - Warm parchment background (`#F8F6F0`), deep ink text (`#141C24`), botanical clinic green accent (`#1B4332`), and warm terracotta.
   - Serif headings, sans-serif UI, and tabular monospace for times, IDs, and masked phones (`••••••3210`).
   - Accessible WCAG AA contrast (>5:1 to 14:1 across all elements) and `prefers-reduced-motion` compliance.
5. **Real-Time Synchronization**:
   - Server-Sent Events (`/api/events`) stream updates to the dashboard with full payloads; affected rows flash in soft green or red and fade.

---

## Project Structure

```text
doctor-appointment/
├── backend/
│   ├── app.py                   # FastAPI app (WebRTC offer/patch, doctors, appointments, SSE stream)
│   ├── bot.py                   # Pipecat voice pipeline, Silero VAD, Gemini LLM, ElevenLabs STT/TTS
│   ├── store.py                 # Thread-safe appointment & doctor slot store (Asia/Kolkata timezone)
│   ├── tools.py                 # Pipecat FunctionSchema & tool handlers (check, book, cancel)
│   ├── phone.py                 # Phone normalizer (word digits, multipliers, +91/0, 10-digit validation)
│   ├── events.py                # Server-Sent Events broadcaster
│   ├── simulate_conversation.py # Text-mode conversational simulation script
│   ├── test_live_server.py      # HTTP and SSE test script against running server
│   ├── requirements.txt         # Pinned backend dependencies
│   └── tests/
│       ├── test_phone.py        # Phone normalizer test suite
│       ├── test_store.py        # Store concurrency, availability, slot return test suite
│       └── test_tools.py        # Safety guardrails and tool logic test suite
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx             # Brand header and "Try Call" action button
│   │   │   ├── PhoneCallModal.tsx     # Phone call screen modal with ringing/connected/ended
│   │   │   ├── AudioWaveform.tsx      # Web Audio AnalyserNode responsive waveform
│   │   │   ├── DoctorsList.tsx        # Doctors grouped by speciality with time chips
│   │   │   ├── AppointmentsTable.tsx  # Appointments table with masked phone & highlight
│   │   │   └── TranscriptPanel.tsx    # Live conversation transcript stream
│   │   ├── services/
│   │   │   └── audio.ts               # Web Audio synthesizer (ringback tone & disconnect tone)
│   │   ├── types.ts                   # TypeScript data contracts
│   │   ├── App.tsx                    # Main app state & WebRTC connection coordinator
│   │   └── index.css                  # Restrained clinic design system
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── screenshots/                 # Headless browser verification screenshots (1440px & 390px)
├── .env.example                 # Example environment variables
├── .gitignore
├── GATES.md                     # Acceptance ledger with proof for every requirement
├── PIPELINE.md                  # Concise voice pipeline architecture explanation (<200 words)
├── DEMO_SCRIPT.md               # 2:30 min script for recording demonstration video
├── pytest.ini
└── README.md
```

---

## Prerequisites

1. **Python 3.12** (C++ Build tools or precompiled wheels for `av`, `aiortc`, `onnxruntime`).
2. **Node.js 18+** (v20+ or v24+ recommended) and `npm`.
3. **API Keys**:
   - **Google Gemini API Key**: Free tier available from [Google AI Studio](https://aistudio.google.com).
   - **ElevenLabs API Key**: Available from [ElevenLabs](https://elevenlabs.io).

---

## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your credentials:
   ```env
   # Google Gemini API Key
   GOOGLE_API_KEY=AIzaSy...

   # Free-tier Flash model
   GEMINI_MODEL=gemini-2.5-flash

   # ElevenLabs API Key & Voice ID
   ELEVENLABS_API_KEY=sk_...
   ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
   ```

---

## Exact Run Commands

### 1. Backend Setup & Run

In a terminal:
```bash
# Create and activate Python 3.12 virtual environment
py -3.12 -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Start backend server (FastAPI + Uvicorn on port 8000)
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup & Run

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

## Testing & Verification

### Run Automated Backend Tests (Pytest)
Executes 22 comprehensive unit tests covering phone normalization, slot allocation, double-booking rejection, unconfirmed phone enforcement, and slot restoration:
```bash
pytest backend/tests/ -v
```

### Run Text-Mode Dialogue Simulation
Simulates the conversational tool execution without requiring audio hardware:
```bash
python backend/simulate_conversation.py
```

### Test Live API & SSE Stream Against Running Server
```bash
python backend/test_live_server.py
```

### Build & Type-Check Frontend
```bash
cd frontend
npm run build
```

---

## How to Test a Voice Call in the Browser

1. Ensure the backend is running (`http://127.0.0.1:8000`) with valid `GOOGLE_API_KEY` and `ELEVENLABS_API_KEY` in `.env`.
2. Open `http://localhost:5173` in Chrome or Edge.
3. Click the **"Try Call"** button in the top right.
4. When prompted by the browser, **Allow microphone access**.
5. Listen for the synthesized ringing tone. When connected, the timer starts and "Maya" greets you:
   > *"Hello, thank you for calling City Care Clinic. How can I help you today?"*
6. Speak:
   > *"I'd like to book an appointment with Dr. Priya Iyer tomorrow morning."*
7. Maya checks availability and gives available slot options (e.g. 09:00 AM).
8. Speak:
   > *"09:00 AM works. My name is Rahul Sharma, and my phone number is 9876543210."*
9. Maya reads back the number:
   > *"I have your number as 9 8 7 6 5, 4 3 2 1 0. Is that correct?"*
10. Say:
    > *"Yes."*
11. The confirmation card slides into the phone, the appointment row flashes green on the dashboard, and Dr. Iyer's available slots decrement.

---

## Known Limitations

1. **Browser Microphone Permissions**: In headless or non-HTTPS production environments, browsers block `navigator.mediaDevices.getUserMedia` unless hosted on `localhost` / `127.0.0.1` or configured with SSL certificates.
2. **STT Latency & Accents**: Spoken numbers with heavy accents or rapid speech may occasionally misrecognize digits. The agent's mandatory read-back guardrail safely intercepts this and lets callers correct the number before any booking is committed.
3. **In-Memory Mock Store**: Appointments and schedules are stored in-memory (seeded relative to today's date in Asia/Kolkata). Restarting the backend server resets the mock clinic data.
