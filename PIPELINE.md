# Voice Pipeline Architecture

The assistant runs on an asynchronous Pipecat audio pipeline with seven sequential stages:

1. **Transport Input**: WebRTC receives 16kHz caller audio from the browser, running Silero VAD to detect when speech starts and stops with low latency.
2. **RTVI Processor**: Relays live audio state and user/agent transcript events directly to the browser dashboard.
3. **Speech-to-Text (ElevenLabs)**: Converts caller audio into real-time text streams.
4. **User Context Aggregator**: Appends transcribed caller utterances into the active conversational context.
5. **LLM Service (Google Gemini Flash)**: Reasons over caller intent under strict short-reply instructions. Three tools plug in directly here via native function calling:
   - `check_doctor_availability`: Queries matching doctors, 30-minute slots, or nearby alternatives.
   - `book_appointment`: Books a slot after validating a 10-digit Indian mobile number and phone confirmation.
   - `cancel_appointment`: Cancels the patient's existing appointment and restores the slot to the open pool.
6. **Text-to-Speech (ElevenLabs)**: Converts the agent's concise 1-2 sentence response into natural streaming speech.
7. **Transport Output & Assistant Aggregator**: Streams synthetic audio back over WebRTC to the caller while appending the assistant's reply into context for subsequent turns.
