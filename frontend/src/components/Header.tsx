import React from "react";
import { Phone } from "lucide-react";

interface HeaderProps {
  onStartCall: () => void;
  isCallActive: boolean;
  sseConnected: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onStartCall,
  isCallActive,
  sseConnected,
}) => {
  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-mark" aria-hidden="true">
          <span>+</span>
        </div>
        <div>
          <h1 className="brand-title">City Care Clinic</h1>
          <p className="brand-subtitle">Voice Appointment Desk • Kolkata</p>
        </div>
      </div>

      <div className="header-actions">
        <div className="status-pill" title={sseConnected ? "Live event stream connected" : "Connecting to stream..."}>
          <span className={`status-dot ${sseConnected ? "connected" : "connecting"}`} />
          <span className="status-text">{sseConnected ? "Live Sync Active" : "Connecting..."}</span>
        </div>

        <button
          className="try-call-button"
          onClick={onStartCall}
          disabled={isCallActive}
          aria-label="Start voice appointment call"
        >
          <Phone size={18} aria-hidden="true" />
          <span>{isCallActive ? "Call in Progress" : "Try Call"}</span>
        </button>
      </div>
    </header>
  );
};
