import React, { useEffect, useRef } from "react";
import type { TranscriptItem } from "../types";
import { MessageSquare, Volume2, User } from "lucide-react";

interface TranscriptPanelProps {
  transcript: TranscriptItem[];
  isCallActive: boolean;
}

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({
  transcript,
  isCallActive,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript]);

  return (
    <div className="card-panel transcript-panel">
      <div className="panel-header-row">
        <div>
          <h2 className="panel-title">Live Transcript</h2>
          <p className="panel-caption">Real-time caller & agent dialogue</p>
        </div>
        {isCallActive && (
          <span className="live-badge" aria-label="Live audio stream in progress">
            <span className="live-indicator" />
            LIVE
          </span>
        )}
      </div>

      <div className="transcript-scroll-area" ref={scrollRef}>
        {transcript.length === 0 ? (
          <div className="empty-state">
            <MessageSquare size={32} className="empty-icon" aria-hidden="true" />
            <p className="empty-title">Transcript will appear here</p>
            <p className="empty-subtitle">
              Press "Try Call" to start speaking with the assistant.
            </p>
          </div>
        ) : (
          <div className="transcript-flow">
            {transcript.map((item) => {
              const isBot = item.role === "bot";

              return (
                <div
                  key={item.id}
                  className={`transcript-bubble ${isBot ? "bot-bubble" : "user-bubble"} ${
                    !item.isFinal ? "interim" : ""
                  }`}
                >
                  <div className="bubble-header">
                    <span className="speaker-name">
                      {isBot ? (
                        <>
                          <Volume2 size={13} aria-hidden="true" />
                          <span>Maya (Agent)</span>
                        </>
                      ) : (
                        <>
                          <User size={13} aria-hidden="true" />
                          <span>Caller</span>
                        </>
                      )}
                    </span>
                    <span className="mono-time bubble-time">{item.timestamp}</span>
                  </div>
                  <div className="bubble-text">
                    {item.text}
                    {!item.isFinal && <span className="cursor-blink" aria-hidden="true">▍</span>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
