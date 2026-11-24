import React, { useEffect, useState, useRef, useCallback } from "react";
import { Header } from "./components/Header";
import { DoctorsList } from "./components/DoctorsList";
import { AppointmentsTable } from "./components/AppointmentsTable";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { PhoneCallModal } from "./components/PhoneCallModal";
import type {
  Appointment,
  BookingNotification,
  CallState,
  Doctor,
  TranscriptItem,
} from "./types";
import { soundManager } from "./services/audio";
import { PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

export const App: React.FC = () => {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [isLoadingDoctors, setIsLoadingDoctors] = useState<boolean>(true);
  const [isLoadingAppointments, setIsLoadingAppointments] = useState<boolean>(true);
  const [doctorsError, setDoctorsError] = useState<string | null>(null);
  const [sseConnected, setSseConnected] = useState<boolean>(false);
  const [highlightedAptId, setHighlightedAptId] = useState<string | null>(null);

  // Call state
  const [callState, setCallState] = useState<CallState>("idle");
  const [callErrorMessage, setCallErrorMessage] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isBotSpeaking, setIsBotSpeaking] = useState<boolean>(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState<boolean>(false);
  const [notification, setNotification] = useState<BookingNotification | null>(null);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);

  // WebRTC & Audio references
  const pipecatClientRef = useRef<PipecatClient | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);
  const remoteAudioElemRef = useRef<HTMLAudioElement | null>(null);
  const ringSoundRef = useRef<{ stop: () => void } | null>(null);

  // Fetch doctors from backend
  const fetchDoctors = useCallback(async () => {
    try {
      const res = await fetch("/api/doctors");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Doctor[] = await res.json();
      setDoctors(data);
      setDoctorsError(null);
    } catch (e) {
      setDoctorsError("Failed to load doctor schedules.");
    } finally {
      setIsDoctorsLoading(false);
    }
  }, []);

  const setIsDoctorsLoading = (v: boolean) => setIsLoadingDoctors(v);

  // Fetch appointments from backend
  const fetchAppointments = useCallback(async () => {
    try {
      const res = await fetch("/api/appointments");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Appointment[] = await res.json();
      setAppointments(data);
    } catch {
      // Keep previous state
    } finally {
      setIsLoadingAppointments(false);
    }
  }, []);

  // Set up Server-Sent Events (SSE) for live dashboard sync
  useEffect(() => {
    fetchDoctors();
    fetchAppointments();

    const eventSource = new EventSource("/api/events");

    eventSource.onopen = () => {
      setSseConnected(true);
    };

    eventSource.addEventListener("message", (event) => {
      try {
        const parsed = JSON.parse(event.data);
        const { type, payload } = parsed;

        if (type === "availability_checked") {
          // Refresh doctors availability
          fetchDoctors();
        } else if (type === "appointment_booked") {
          const apt: Appointment = payload.appointment;
          setHighlightedAptId(apt.appointment_id);
          fetchDoctors();
          fetchAppointments();

          // Trigger notification card inside phone
          setNotification({
            type: "booked",
            appointment_id: apt.appointment_id,
            doctor_name: apt.doctor_name,
            date: apt.date,
            time: apt.time,
          });

          // Clear highlight after 4s
          setTimeout(() => {
            setHighlightedAptId((current) =>
              current === apt.appointment_id ? null : current
            );
          }, 4500);
        } else if (type === "appointment_cancelled") {
          const aptId: string = payload.appointment_id;
          setHighlightedAptId(aptId);
          fetchDoctors();
          fetchAppointments();

          // Trigger notification card inside phone
          setNotification({
            type: "cancelled",
            appointment_id: aptId,
            doctor_name: payload.doctor_name,
            date: payload.date,
            time: payload.time,
          });

          setTimeout(() => {
            setHighlightedAptId((current) =>
              current === aptId ? null : current
            );
          }, 4500);
        }
      } catch (e) {
        console.error("Error processing SSE message:", e);
      }
    });

    eventSource.onerror = () => {
      setSseConnected(false);
    };

    return () => {
      eventSource.close();
    };
  }, [fetchDoctors, fetchAppointments]);

  // Helper to append or update transcript
  const appendTranscript = (role: "user" | "bot", text: string, isFinal: boolean) => {
    if (!text.trim()) return;
    const now = new Date().toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });

    setTranscript((prev) => {
      // If last item is interim and same role, update it
      const last = prev[prev.length - 1];
      if (last && last.role === role && !last.isFinal) {
        return [
          ...prev.slice(0, -1),
          { ...last, text, isFinal, timestamp: now },
        ];
      }
      return [
        ...prev,
        {
          id: Math.random().toString(36).substring(2, 9),
          role,
          text,
          isFinal,
          timestamp: now,
        },
      ];
    });
  };

  // Start Voice Call
  const handleStartCall = async () => {
    setCallErrorMessage(null);
    setNotification(null);
    setCallState("ringing");
    setIsMuted(false);

    // Play synthesized Web Audio ring tone
    ringSoundRef.current = soundManager.startRingTone();

    try {
      // 1. Request user microphone
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      localStreamRef.current = stream;

      // 2. STUN & TURN servers for reliable WebRTC NAT & cloud relay traversal
      let iceServers: RTCIceServer[] = [
        {
          urls: [
            "stun:stun.l.google.com:19302",
            "stun:stun1.l.google.com:19302",
            "stun:openrelay.metered.ca:80",
          ],
        },
        {
          urls: [
            "turn:openrelay.metered.ca:80",
            "turn:openrelay.metered.ca:443",
            "turn:openrelay.metered.ca:443?transport=tcp",
            "turns:openrelay.metered.ca:443",
          ],
          username: "openrelayproject",
          credential: "openrelayproject",
        },
      ];

      try {
        const iceRes = await fetch("/api/ice-servers");
        if (iceRes.ok) {
          const customServers = await iceRes.json();
          if (Array.isArray(customServers) && customServers.length > 0) {
            iceServers = customServers;
          }
        }
      } catch (err) {
        console.warn("Could not fetch /api/ice-servers, using default ICE servers:", err);
      }

      // Initialize SmallWebRTCTransport with STUN and TURN
      const transport = new SmallWebRTCTransport({
        webrtcRequestParams: {
          endpoint: "/api/offer",
        },
        iceServers,
      });

      // 3. Initialize PipecatClient (voice-only: mic enabled, camera disabled)
      const client = new PipecatClient({
        transport,
        enableCam: false,
        enableMic: true,
      });
      pipecatClientRef.current = client;

      const attachRemoteTrack = (track: MediaStreamTrack) => {
        if (track && track.kind === "audio") {
          console.log("Attached remote bot audio track:", track);
          const remoteStream = new MediaStream([track]);
          remoteStreamRef.current = remoteStream;
          if (remoteAudioElemRef.current) {
            remoteAudioElemRef.current.srcObject = remoteStream;
            remoteAudioElemRef.current.muted = false;
            remoteAudioElemRef.current.play().catch((e) => console.warn("Audio play:", e));
          }
        }
      };

      // Setup RTVI events
      client.on(RTVIEvent.Connected, () => {
        console.log("Pipecat Connected event received");
        ringSoundRef.current?.stop();
        setCallState("connected");
        const allTracks = client.tracks();
        if (allTracks?.bot?.audio) {
          attachRemoteTrack(allTracks.bot.audio);
        }
      });

      client.on(RTVIEvent.BotReady, () => {
        console.log("Pipecat BotReady event received");
        ringSoundRef.current?.stop();
        setCallState("connected");
        const allTracks = client.tracks();
        if (allTracks?.bot?.audio) {
          attachRemoteTrack(allTracks.bot.audio);
        }
      });

      client.on(RTVIEvent.BotStartedSpeaking, () => {
        setIsBotSpeaking(true);
      });

      client.on(RTVIEvent.BotStoppedSpeaking, () => {
        setIsBotSpeaking(false);
      });

      client.on(RTVIEvent.UserStartedSpeaking, () => {
        setIsUserSpeaking(true);
      });

      client.on(RTVIEvent.UserStoppedSpeaking, () => {
        setIsUserSpeaking(false);
      });

      client.on(RTVIEvent.UserTranscript, (data: { text: string; final: boolean }) => {
        console.log("User transcript:", data);
        appendTranscript("user", data.text, data.final);
      });

      client.on(RTVIEvent.BotTranscript, (data: { text: string }) => {
        console.log("Bot transcript:", data);
        appendTranscript("bot", data.text, true);
      });

      client.on(RTVIEvent.TrackStarted, (track: MediaStreamTrack) => {
        console.log("TrackStarted event received:", track);
        attachRemoteTrack(track);
      });

      client.on(RTVIEvent.Error, (err: unknown) => {
        console.error("Pipecat Client Error:", err);
        ringSoundRef.current?.stop();
        setCallErrorMessage("Connection encountered an error. Please try again.");
        setCallState("error");
      });

      client.on(RTVIEvent.Disconnected, () => {
        console.log("Pipecat Disconnected event received");
        handleEndCall();
      });

      // Initialize media devices and connect transport
      await client.initDevices();
      await client.connect();
    } catch (err: unknown) {
      ringSoundRef.current?.stop();
      console.error("Start call failure:", err);
      const msg =
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone permission was denied. Please allow microphone access to speak."
          : (err as Error)?.message || "Could not establish connection to the voice assistant.";
      setCallErrorMessage(msg);
      setCallState("error");
    }
  };

  // Toggle Mute
  const handleToggleMute = () => {
    if (localStreamRef.current) {
      const nextMute = !isMuted;
      localStreamRef.current.getAudioTracks().forEach((t) => {
        t.enabled = !nextMute;
      });
      setIsMuted(nextMute);
      if (pipecatClientRef.current) {
        pipecatClientRef.current.enableMic(!nextMute);
      }
    }
  };

  // End Call
  const handleEndCall = () => {
    ringSoundRef.current?.stop();

    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((t) => t.stop());
      localStreamRef.current = null;
    }

    if (pipecatClientRef.current) {
      try {
        pipecatClientRef.current.disconnect();
      } catch {
        // ignore
      }
      pipecatClientRef.current = null;
    }

    if (callState === "connected" || callState === "ringing") {
      soundManager.playEndCallTone();
      setCallState("ended");
    } else {
      setCallState("idle");
    }
  };

  return (
    <div className="clinic-app">
      {/* Hidden element for remote assistant audio playback */}
      <audio ref={remoteAudioElemRef} autoPlay playsInline />

      <Header
        onStartCall={handleStartCall}
        isCallActive={callState === "connected" || callState === "ringing"}
        sseConnected={sseConnected}
      />

      <main className="dashboard-layout">
        {/* Left Column: Live Transcript Panel */}
        <section className="dashboard-left" aria-label="Conversation Transcript">
          <TranscriptPanel
            transcript={transcript}
            isCallActive={callState === "connected"}
          />
        </section>

        {/* Right Column: Doctors & Appointments */}
        <section className="dashboard-right" aria-label="Clinic Schedule and Appointments">
          <DoctorsList
            doctors={doctors}
            isLoading={isLoadingDoctors}
            error={doctorsError}
          />

          <AppointmentsTable
            appointments={appointments}
            highlightedAptId={highlightedAptId}
            isLoading={isLoadingAppointments}
          />
        </section>
      </main>

      {/* Phone-Style Call Modal Screen */}
      <PhoneCallModal
        callState={callState}
        errorMessage={callErrorMessage}
        onEndCall={callState === "ended" ? () => setCallState("idle") : handleEndCall}
        onRetry={handleStartCall}
        onToggleMute={handleToggleMute}
        isMuted={isMuted}
        transcript={transcript}
        notification={notification}
        localStream={localStreamRef.current}
        remoteStream={remoteStreamRef.current}
        isBotSpeaking={isBotSpeaking}
        isUserSpeaking={isUserSpeaking}
      />
    </div>
  );
};

export default App;
