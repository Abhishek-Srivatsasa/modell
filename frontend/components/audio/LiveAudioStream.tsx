"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────
interface AudioResult {
  audio_risk_score: number;
  audio_verdict: "real" | "fake" | "suspicious" | "pending" | "unavailable" | "error";
  audio_confidence: number;
  model_available: boolean;
  chunk_count: number;
  inference_count: number;
  session_id: string;
}

interface LiveAudioStreamProps {
  sessionId: string;
  wsBaseUrl?: string;
  onResult?: (result: AudioResult) => void;
}

type ConnectionState = "idle" | "connecting" | "connected" | "disconnected" | "error";

// ── Constants ─────────────────────────────────────────────────────────────────
const CHUNK_INTERVAL_MS = 1000; // Send 1s chunks — backend buffers 5 → 5s inference
const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECTS = 5;

// ── Component ─────────────────────────────────────────────────────────────────
export default function LiveAudioStream({
  sessionId,
  wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000",
  onResult,
}: LiveAudioStreamProps) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [result, setResult] = useState<AudioResult | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chunkssent, setChunksSent] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── WebSocket ───────────────────────────────────────────────────────────────
  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionState("connecting");
    const url = `${wsBaseUrl}/ws/live-audio/${sessionId}`;
    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState("connected");
      setError(null);
      reconnectCountRef.current = 0;
    };

    ws.onmessage = (evt) => {
      try {
        const data: AudioResult = JSON.parse(
          typeof evt.data === "string" ? evt.data : new TextDecoder().decode(evt.data)
        );
        setResult(data);
        onResult?.(data);
      } catch {
        // Non-JSON message — ignore
      }
    };

    ws.onclose = () => {
      setConnectionState("disconnected");
      scheduleReconnect();
    };

    ws.onerror = () => {
      setConnectionState("error");
      setError("WebSocket connection failed");
    };
  }, [sessionId, wsBaseUrl, onResult]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectCountRef.current >= MAX_RECONNECTS) return;
    reconnectCountRef.current += 1;
    reconnectTimerRef.current = setTimeout(connectWS, RECONNECT_DELAY_MS);
  }, [connectWS]);

  // ── MediaRecorder ───────────────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      streamRef.current = stream;

      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (evt) => {
        if (
          evt.data.size > 0 &&
          wsRef.current?.readyState === WebSocket.OPEN
        ) {
          wsRef.current.send(evt.data);
          setChunksSent((n) => n + 1);
        }
      };

      recorder.start(CHUNK_INTERVAL_MS); // fires ondataavailable every 1s
      setIsRecording(true);
      connectWS();
    } catch (err) {
      setError("Microphone access denied. Please allow microphone permissions.");
    }
  }, [connectWS]);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    wsRef.current?.close();
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    setIsRecording(false);
    setConnectionState("idle");
    setResult(null);
    setChunksSent(0);
  }, []);

  // ── Cleanup ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, [stopRecording]);

  // ── Derived UI values ───────────────────────────────────────────────────────
  const riskPercent = result ? Math.round(result.audio_risk_score * 100) : 0;
  const verdictColor = {
    real: "#00ff88",
    fake: "#ff3b3b",
    suspicious: "#ffaa00",
    pending: "#888",
    unavailable: "#888",
    error: "#ff3b3b",
  }[result?.audio_verdict ?? "pending"];

  const verdictLabel = {
    real: "✓ AUTHENTIC",
    fake: "⚠ DEEPFAKE DETECTED",
    suspicious: "~ SUSPICIOUS",
    pending: "ANALYZING...",
    unavailable: "MODEL UNAVAILABLE",
    error: "INFERENCE ERROR",
  }[result?.audio_verdict ?? "pending"];

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-6 w-full max-w-xl mx-auto">
      {/* Status bar */}
      <div className="flex items-center justify-between px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-700">
        <span className="text-xs font-mono text-zinc-400">
          SESSION: {sessionId.slice(0, 8).toUpperCase()}
        </span>
        <span
          className="text-xs font-mono uppercase"
          style={{
            color:
              connectionState === "connected"
                ? "#00ff88"
                : connectionState === "error"
                ? "#ff3b3b"
                : "#888",
          }}
        >
          ● {connectionState}
        </span>
      </div>

      {/* Risk gauge */}
      <div className="relative flex flex-col items-center justify-center p-8 rounded-2xl bg-zinc-900 border border-zinc-800">
        {/* Circular progress */}
        <svg width="160" height="160" className="mb-4">
          <circle cx="80" cy="80" r="68" fill="none" stroke="#27272a" strokeWidth="12" />
          <circle
            cx="80"
            cy="80"
            r="68"
            fill="none"
            stroke={verdictColor}
            strokeWidth="12"
            strokeDasharray={`${2 * Math.PI * 68}`}
            strokeDashoffset={`${2 * Math.PI * 68 * (1 - riskPercent / 100)}`}
            strokeLinecap="round"
            transform="rotate(-90 80 80)"
            style={{ transition: "stroke-dashoffset 0.6s ease, stroke 0.4s ease" }}
          />
          <text x="80" y="75" textAnchor="middle" fill="white" fontSize="28" fontWeight="bold" fontFamily="monospace">
            {riskPercent}%
          </text>
          <text x="80" y="96" textAnchor="middle" fill="#71717a" fontSize="11" fontFamily="monospace">
            FAKE PROBABILITY
          </text>
        </svg>

        {/* Verdict label */}
        <span
          className="text-sm font-mono font-bold tracking-widest"
          style={{ color: verdictColor }}
        >
          {verdictLabel}
        </span>

        {/* Waveform animation while recording */}
        {isRecording && (
          <div className="flex items-end gap-0.5 mt-4 h-8">
            {Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="w-1 rounded-full"
                style={{
                  backgroundColor: verdictColor,
                  height: `${20 + Math.random() * 60}%`,
                  animation: `pulse ${0.4 + Math.random() * 0.6}s ease-in-out infinite alternate`,
                  animationDelay: `${i * 0.05}s`,
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "CHUNKS SENT", value: chunkssent },
          { label: "INFERENCES", value: result?.inference_count ?? 0 },
          { label: "CONFIDENCE", value: `${riskPercent}%` },
        ].map(({ label, value }) => (
          <div key={label} className="flex flex-col items-center p-3 rounded-xl bg-zinc-900 border border-zinc-800">
            <span className="text-lg font-mono font-bold text-white">{value}</span>
            <span className="text-xs font-mono text-zinc-500 mt-0.5">{label}</span>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-950 border border-red-800 text-red-400 text-sm font-mono">
          {error}
        </div>
      )}

      {/* Control button */}
      <button
        onClick={isRecording ? stopRecording : startRecording}
        className="w-full py-4 rounded-xl font-mono font-bold text-sm tracking-widest uppercase transition-all duration-200"
        style={{
          backgroundColor: isRecording ? "#3f0000" : "#003f1a",
          color: isRecording ? "#ff3b3b" : "#00ff88",
          border: `1px solid ${isRecording ? "#ff3b3b44" : "#00ff8844"}`,
        }}
      >
        {isRecording ? "⬛ STOP ANALYSIS" : "⏺ START AUDIO ANALYSIS"}
      </button>

      <style>{`
        @keyframes pulse {
          from { transform: scaleY(0.4); }
          to   { transform: scaleY(1); }
        }
      `}</style>
    </div>
  );
}
