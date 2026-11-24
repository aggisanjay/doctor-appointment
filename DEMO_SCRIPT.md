# Demo Video Recording Script (2:30 Minutes)

A complete spoken script for recording the demonstration video of City Care Clinic's voice assistant.
Demonstrates: availability check, phone digit readback confirmation, live booking with dashboard highlight, and subsequent cancellation with slot restoration.

---

### [0:00 - 0:20] Setup & Initial State
- **Screen View**: Show full browser window on desktop (1440px) with the dashboard open (`http://localhost:5173`).
- **Visual Cue**: Point out the live doctors schedule (Dr. Aarav Sharma, Dr. Priya Iyer, etc.) with 60 available slots each for the next 5 days, and the "No appointments yet" empty state table.
- **Presenter Spoken Voiceover**:
  > *"Welcome to City Care Clinic. Today we are demonstrating our voice-based appointment assistant built with Pipecat, ElevenLabs, and Google Gemini Flash. Let's start a call."*
- **Action**: Click the **"Try Call"** button in the header.

---

### [0:20 - 0:40] Call Connecting & Greeting
- **Screen View**: The phone-style call screen modal slides into view. The Web Audio PBX ringtone plays as the agent connects.
- **Audio Transition**: Ring tone stops; call timer starts at `00:00`.
- **Maya (Voice Assistant)**:
  > *"Hello, thank you for calling City Care Clinic. How can I help you today?"*
- **Caller (You)**:
  > *"Hi Maya, I'd like to check if you have a cardiologist available tomorrow morning."*

---

### [0:40 - 1:10] Availability Check & Slot Selection
- **Visual Cue**: Tool `check_doctor_availability` runs in backend; waveform bars react to speech.
- **Maya (Voice Assistant)**:
  > *"Dr. Priya Iyer has openings tomorrow at 09:00 AM and 09:30 AM. Would one of those times suit you?"*
- **Caller (You)**:
  > *"Nine AM sounds great. My name is Rajesh Patel, and my number is 9 8 7 6 5 4 3 2 1 0."*

---

### [1:10 - 1:40] Phone Readback Confirmation & Live Booking
- **Visual Cue**: Notice that the backend strictly enforces phone confirmation in code before executing `book_appointment`.
- **Maya (Voice Assistant)**:
  > *"I have your number as 9 8 7 6 5, 4 3 2 1 0. Is that correct?"*
- **Caller (You)**:
  > *"Yes, that is correct."*
- **Visual Cue**:
  1. The green **"Booking Confirmed"** card slides into the phone screen with Dr. Priya Iyer, date, and 09:00 AM.
  2. In the background dashboard, appointment row `APT-1001` appears in the table with phone masked as `••••••3210` and **highlights in soft green**.
  3. Dr. Priya Iyer's available slots decrement from 60 to 59 in real time.
- **Maya (Voice Assistant)**:
  > *"Your appointment with Dr. Priya Iyer for tomorrow at 09:00 AM is confirmed."*

---

### [1:40 - 2:10] Cancellation Flow & Slot Restoration
- **Caller (You)**:
  > *"Actually Maya, something came up and I need to cancel that appointment."*
- **Maya (Voice Assistant)**:
  > *"I can assist with that. To confirm, may I cancel the appointment for number ending in 3 2 1 0?"*
- **Caller (You)**:
  > *"Yes, please cancel it."*
- **Visual Cue**:
  1. The red **"Appointment Cancelled"** card slides into the phone screen.
  2. On the dashboard, `APT-1001` row flashes and transitions to `Cancelled` status.
  3. Dr. Priya Iyer's 09:00 AM slot immediately returns to the free slots schedule.
- **Maya (Voice Assistant)**:
  > *"Your appointment with Dr. Priya Iyer for tomorrow at 09:00 AM has been cancelled."*

---

### [2:10 - 2:30] Call Wrap-Up & Conclusion
- **Action**: Click the red **"End"** call button.
- **Audio Cue**: Web Audio plays the 3-pulse telephony disconnect tone.
- **Screen View**: Phone shows "Call Ended after 01:45. Your appointments are updated on the dashboard." Click "Done" to dismiss.
- **Presenter Spoken Voiceover**:
  > *"The call is ended cleanly. The live transcript captured the entire dialogue, and the appointments ledger and slot availability reflect the exact state through real-time Server-Sent Events. Thank you."*
