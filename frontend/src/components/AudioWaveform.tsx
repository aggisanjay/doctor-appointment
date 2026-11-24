import React, { useEffect, useRef } from "react";

interface AudioWaveformProps {
  localStream: MediaStream | null;
  remoteStream: MediaStream | null;
  isMuted: boolean;
  isBotSpeaking: boolean;
  isUserSpeaking: boolean;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({
  localStream,
  remoteStream,
  isMuted,
  isBotSpeaking,
  isUserSpeaking,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      // Draw static peaceful state
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#1E4D38";
        const barWidth = 4;
        const count = 16;
        const startX = (canvas.width - count * 8) / 2;
        for (let i = 0; i < count; i++) {
          const h = 8 + (i % 3) * 4;
          ctx.fillRect(startX + i * 8, (canvas.height - h) / 2, barWidth, h);
        }
      }
      return;
    }

    let audioCtx: AudioContext | null = null;
    let localAnalyser: AnalyserNode | null = null;
    let remoteAnalyser: AnalyserNode | null = null;
    let localSource: MediaStreamAudioSourceNode | null = null;
    let remoteSource: MediaStreamAudioSourceNode | null = null;

    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      audioCtx = new AudioCtx();

      if (localStream && localStream.getAudioTracks().length > 0 && !isMuted) {
        localAnalyser = audioCtx.createAnalyser();
        localAnalyser.fftSize = 64;
        localAnalyser.smoothingTimeConstant = 0.7;
        localSource = audioCtx.createMediaStreamSource(localStream);
        localSource.connect(localAnalyser);
      }

      if (remoteStream && remoteStream.getAudioTracks().length > 0) {
        remoteAnalyser = audioCtx.createAnalyser();
        remoteAnalyser.fftSize = 64;
        remoteAnalyser.smoothingTimeConstant = 0.7;
        remoteSource = audioCtx.createMediaStreamSource(remoteStream);
        remoteSource.connect(remoteAnalyser);
      }
    } catch (e) {
      console.warn("Waveform audio context initialization:", e);
    }

    const localData = new Uint8Array(32);
    const remoteData = new Uint8Array(32);

    const render = () => {
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      let localVol = 0;
      let remoteVol = 0;

      if (localAnalyser && !isMuted) {
        localAnalyser.getByteFrequencyData(localData);
        let sum = 0;
        for (let i = 0; i < localData.length; i++) sum += localData[i];
        localVol = sum / localData.length / 255;
      }

      if (remoteAnalyser) {
        remoteAnalyser.getByteFrequencyData(remoteData);
        let sum = 0;
        for (let i = 0; i < remoteData.length; i++) sum += remoteData[i];
        remoteVol = sum / remoteData.length / 255;
      }

      // Boost volume if speaking state flags are true
      if (isUserSpeaking && localVol < 0.2) localVol = 0.35 + Math.random() * 0.2;
      if (isBotSpeaking && remoteVol < 0.2) remoteVol = 0.45 + Math.random() * 0.25;

      const activeVol = Math.max(localVol, remoteVol);
      const isAgentActive = remoteVol > localVol && isBotSpeaking;

      // Draw modern symmetrical voice bars (18 bars)
      const numBars = 18;
      const barWidth = 3;
      const barGap = 4;
      const totalWidth = numBars * (barWidth + barGap);
      const startX = (width - totalWidth) / 2;

      for (let i = 0; i < numBars; i++) {
        const x = startX + i * (barWidth + barGap);
        // Distance from center bell curve factor
        const distFromCenter = Math.abs(i - (numBars - 1) / 2) / ((numBars - 1) / 2);
        const curveFactor = Math.cos(distFromCenter * (Math.PI / 2.2));

        const baseHeight = 4;
        const dynamicHeight = Math.max(
          baseHeight,
          activeVol * (height * 0.75) * curveFactor * (0.8 + Math.sin(Date.now() / 150 + i * 0.5) * 0.2)
        );

        const y = (height - dynamicHeight) / 2;

        // Bar colors: Forest green for bot, deep slate for user, muted grey when idle
        if (isAgentActive) {
          ctx.fillStyle = "#1E4D38"; // Clinic botanical green
        } else if (localVol > 0.05 && !isMuted) {
          ctx.fillStyle = "#334155"; // Caller slate
        } else {
          ctx.fillStyle = "#CBD5E1"; // Idle quiet bar
        }

        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, dynamicHeight, 2);
        ctx.fill();
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
      try {
        localSource?.disconnect();
        remoteSource?.disconnect();
        audioCtx?.close();
      } catch (e) {
        // cleanup ignore
      }
    };
  }, [localStream, remoteStream, isMuted, isBotSpeaking, isUserSpeaking]);

  return (
    <div className="waveform-container" aria-label="Live voice audio indicator" role="img">
      <canvas
        ref={canvasRef}
        width={180}
        height={48}
        className="waveform-canvas"
      />
    </div>
  );
};
