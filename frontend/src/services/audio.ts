/**
 * Web Audio tone synthesizer and audio analyser.
 * Generates realistic telephony ring and end tones with 0 asset files.
 */

class SoundSynthesizer {
  private audioCtx: AudioContext | null = null;
  private ringInterval: number | null = null;
  private isRinging = false;

  private getContext(): AudioContext {
    if (!this.audioCtx || this.audioCtx.state === "closed") {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.audioCtx = new AudioCtx();
    }
    if (this.audioCtx.state === "suspended") {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  /**
   * Starts a realistic dual-tone PBX ringback tone (400Hz + 450Hz).
   * Cadence: 0.4s tone, 0.2s pause, 0.4s tone, 2s silence.
   */
  startRingTone(): { stop: () => void } {
    this.stopRingTone();
    this.isRinging = true;

    const playBurst = (durationSec: number) => {
      if (!this.isRinging) return;
      try {
        const ctx = this.getContext();
        const now = ctx.currentTime;

        const osc1 = ctx.createOscillator();
        const osc2 = ctx.createOscillator();
        const gain = ctx.createGain();

        osc1.type = "sine";
        osc1.frequency.setValueAtTime(400, now);

        osc2.type = "sine";
        osc2.frequency.setValueAtTime(450, now);

        // Gentle envelope to avoid clicks
        gain.gain.setValueAtTime(0.001, now);
        gain.gain.exponentialRampToValueAtTime(0.12, now + 0.05);
        gain.gain.setValueAtTime(0.12, now + durationSec - 0.05);
        gain.gain.exponentialRampToValueAtTime(0.001, now + durationSec);

        osc1.connect(gain);
        osc2.connect(gain);
        gain.connect(ctx.destination);

        osc1.start(now);
        osc2.start(now);
        osc1.stop(now + durationSec);
        osc2.stop(now + durationSec);
      } catch (e) {
        console.warn("Ring sound synthesis error:", e);
      }
    };

    const triggerCycle = () => {
      if (!this.isRinging) return;
      playBurst(0.4);
      setTimeout(() => {
        if (!this.isRinging) return;
        playBurst(0.4);
      }, 600);
    };

    triggerCycle();
    this.ringInterval = window.setInterval(triggerCycle, 3000);

    return {
      stop: () => this.stopRingTone(),
    };
  }

  stopRingTone(): void {
    this.isRinging = false;
    if (this.ringInterval !== null) {
      clearInterval(this.ringInterval);
      this.ringInterval = null;
    }
  }

  /**
   * Plays the standard disconnect / call-ended beep sequence (425Hz, 3 short pulses).
   */
  playEndCallTone(): void {
    this.stopRingTone();
    try {
      const ctx = this.getContext();
      const startTime = ctx.currentTime + 0.05;
      const pulseDuration = 0.18;
      const gap = 0.12;

      for (let i = 0; i < 3; i++) {
        const pulseStart = startTime + i * (pulseDuration + gap);
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = "sine";
        osc.frequency.setValueAtTime(425, pulseStart);

        gain.gain.setValueAtTime(0.001, pulseStart);
        gain.gain.exponentialRampToValueAtTime(0.15, pulseStart + 0.02);
        gain.gain.setValueAtTime(0.15, pulseStart + pulseDuration - 0.02);
        gain.gain.exponentialRampToValueAtTime(0.001, pulseStart + pulseDuration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(pulseStart);
        osc.stop(pulseStart + pulseDuration);
      }
    } catch (e) {
      console.warn("End call sound synthesis error:", e);
    }
  }
}

export const soundManager = new SoundSynthesizer();
