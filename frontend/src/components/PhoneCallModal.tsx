import React, { useEffect, useState, useRef } from "react";
import {
  PhoneOff,
  Mic,
  MicOff,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RotateCcw,
} from "lucide-react";
import type { BookingNotification, CallState, TranscriptItem } from "../types";
import { AudioWaveform } from "./AudioWaveform";

interface PhoneCallModalProps {
  callState: CallState;
  errorMessage: string | null;
  onEndCall: () => void;
  onRetry: () => void;
  onToggleMute: () => void;
  isMuted: boolean;
  transcript: TranscriptItem[];
  notification: BookingNotification | null;
  localStream: MediaStream | null;
  remoteStream: MediaStream | null;
  isBotSpeaking: boolean;
  isUserSpeaking: boolean;
}

export const PhoneCallModal: React.FC<PhoneCallModalProps> = ({
  callState,
  errorMessage,
  onEndCall,
  onRetry,
  onToggleMute,
  isMuted,
  transcript,
  notification,
  localStream,
  remoteStream,
  isBotSpeaking,
  isUserSpeaking,
}) => {
  const [callDuration, setCallDuration] = useState<number>(0);
  const transcriptBottomRef = useRef<HTMLDivElement | null>(null);

  // Call timer during connected state
  useEffect(() => {
    let timer: number | null = null;
    if (callState === "connected") {
      timer = window.setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else if (callState === "ringing") {
      setCallDuration(0);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [callState]);

  // Auto-scroll transcript inside phone
  useEffect(() => {
    transcriptBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const formatTimer = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  if (callState === "idle") {
    return null;
  }

  return (
    <div className="phone-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="phone-caller-name">
      <div className={`phone-chassis ${callState}`}>
        {/* Phone Speaker Notch */}
        <div className="phone-notch" aria-hidden="true">
          <div className="phone-earpiece" />
        </div>

        {/* Header: Caller Details & Status */}
        <div className="phone-header">
          <div className="caller-avatar" aria-hidden="true">
            <span>M</span>
          </div>
          <h2 id="phone-caller-name" className="caller-name">
            Maya
          </h2>
          <p className="caller-org">City Care Clinic</p>

          <div className="call-status-indicator">
            {callState === "ringing" && (
              <span className="status-ringing-text">Calling clinic...</span>
            )}
            {callState === "connected" && (
              <span className="status-connected-timer mono-time">
                {formatTimer(callDuration)}
              </span>
            )}
            {callState === "ended" && (
              <span className="status-ended-text">Call Ended</span>
            )}
            {callState === "error" && (
              <span className="status-error-text">Connection Failed</span>
            )}
          </div>
        </div>

        {/* Middle Screen Area */}
        <div className="phone-screen-content">
          {/* Waveform Visualization (during connected or ringing) */}
          {(callState === "connected" || callState === "ringing") && (
            <div className="waveform-box">
              <AudioWaveform
                localStream={localStream}
                remoteStream={remoteStream}
                isMuted={isMuted}
                isBotSpeaking={isBotSpeaking}
                isUserSpeaking={isUserSpeaking}
              />
              <span className="speaker-label">
                {isBotSpeaking
                  ? "Maya is speaking..."
                  : isUserSpeaking
                  ? "Listening to you..."
                  : "Listening..."}
              </span>
            </div>
          )}

          {/* Slide-in Booking / Cancellation Card */}
          {notification && (
            <div
              className={`confirmation-card ${notification.type}`}
              role="status"
              aria-live="polite"
            >
              <div className="card-badge">
                {notification.type === "booked" ? (
                  <CheckCircle size={18} className="icon-booked" aria-hidden="true" />
                ) : (
                  <XCircle size={18} className="icon-cancelled" aria-hidden="true" />
                )}
                <span className="card-heading">
                  {notification.type === "booked" ? "Booking Confirmed" : "Appointment Cancelled"}
                </span>
              </div>
              <div className="card-details">
                <div className="card-doc">{notification.doctor_name}</div>
                <div className="card-datetime mono-time">
                  {notification.date} at {notification.time}
                </div>
              </div>
            </div>
          )}

          {/* In-Phone Live Transcript Stream */}
          {callState === "connected" && (
            <div className="phone-transcript-viewport">
              <div className="phone-transcript-list">
                {transcript.map((item) => (
                  <div
                    key={item.id}
                    className={`phone-bubble ${item.role === "bot" ? "bot" : "user"} ${
                      !item.isFinal ? "interim" : ""
                    }`}
                  >
                    <span className="phone-bubble-sender">
                      {item.role === "bot" ? "Maya" : "You"}
                    </span>
                    <p className="phone-bubble-content">{item.text}</p>
                  </div>
                ))}
                <div ref={transcriptBottomRef} />
              </div>
            </div>
          )}

          {/* Error Message Screen */}
          {callState === "error" && (
            <div className="phone-error-view">
              <AlertTriangle size={36} className="error-icon" aria-hidden="true" />
              <p className="error-title">Unable to Connect</p>
              <p className="error-desc">{errorMessage || "Microphone access was denied or the server is unreachable."}</p>
              <button className="retry-button" onClick={onRetry}>
                <RotateCcw size={16} aria-hidden="true" />
                <span>Try Again</span>
              </button>
            </div>
          )}

          {/* Ended Screen */}
          {callState === "ended" && (
            <div className="phone-ended-view">
              <p className="ended-summary">
                Call ended after <span className="mono-time">{formatTimer(callDuration)}</span>
              </p>
              <p className="ended-note">Your appointments are updated on the dashboard.</p>
            </div>
          )}
        </div>

        {/* Bottom Call Controls */}
        <div className="phone-controls">
          {callState === "connected" && (
            <button
              className={`control-circle mute-button ${isMuted ? "muted" : ""}`}
              onClick={onToggleMute}
              title={isMuted ? "Unmute microphone" : "Mute microphone"}
              aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
            >
              {isMuted ? <MicOff size={22} /> : <Mic size={22} />}
              <span className="control-label">{isMuted ? "Muted" : "Mute"}</span>
            </button>
          )}

          <button
            className="control-circle end-call-button"
            onClick={onEndCall}
            title={callState === "ended" ? "Close window" : "End Call"}
            aria-label={callState === "ended" ? "Close window" : "End Call"}
          >
            <PhoneOff size={24} />
            <span className="control-label">
              {callState === "ended" ? "Done" : "End"}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};
