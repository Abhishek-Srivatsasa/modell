"use client";

import { useState } from "react";
import LiveAudioStream from "@/components/audio/LiveAudioStream";
import { v4 as uuidv4 } from "uuid";

// Session ID is generated once per page load — same pattern as video verify
const SESSION_ID = uuidv4();

export default function AudioVerifyPage() {
  const [latestResult, setLatestResult] = useState<any>(null);

  return (
    <main className="min-h-screen bg-black text-white flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-5 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          {/* Back to main dashboard — does not affect video pipeline */}
          <a
            href="/dashboard"
            className="text-zinc-500 hover:text-white text-sm font-mono transition-colors"
          >
            ← DASHBOARD
          </a>
          <span className="text-zinc-700">|</span>
          <span className="text-sm font-mono text-zinc-300 tracking-widest uppercase">
            Audio Verification
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-mono text-zinc-400">CNN-BiLSTM ACTIVE</span>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-12 gap-10">
        {/* Title block */}
        <div className="text-center max-w-lg">
          <h1 className="text-3xl font-mono font-bold tracking-tight mb-2">
            Audio Deepfake Detection
          </h1>
          <p className="text-zinc-400 text-sm font-mono leading-relaxed">
            Real-time voice spoofing analysis using a custom{" "}
            <span className="text-emerald-400">CNN-BiLSTM</span> model trained
            on 4,447 samples across 8 modern TTS generators. Speak naturally —
            the system analyzes 5-second windows continuously.
          </p>
        </div>

        {/* Core stream component */}
        <LiveAudioStream
          sessionId={SESSION_ID}
          onResult={setLatestResult}
        />

        {/* Model info card */}
        <div className="w-full max-w-xl rounded-2xl border border-zinc-800 bg-zinc-950 p-6">
          <p className="text-xs font-mono text-zinc-500 uppercase tracking-widest mb-4">
            Model Architecture
          </p>
          <div className="grid grid-cols-2 gap-3 text-xs font-mono">
            {[
              ["Input", "128×109 Mel-Spectrogram"],
              ["Spatial", "3× Conv2D (32→64→128)"],
              ["Temporal", "BiLSTM (64→32 units)"],
              ["Output", "Sigmoid (0=Real, 1=Fake)"],
              ["Training data", "4,447 WAV files"],
              ["Generators", "VoiceBox, xTTS, VALLE, OpenAI TTS"],
            ].map(([k, v]) => (
              <div key={k} className="flex flex-col gap-0.5">
                <span className="text-zinc-600">{k}</span>
                <span className="text-zinc-300">{v}</span>
              </div>
            ))}
          </div>
          <p className="text-xs font-mono text-zinc-600 mt-4 leading-relaxed">
            ⚠ Note: Model analyzes ~5s windows. Detection accuracy may decrease
            with heavily compressed audio or significant background noise.
          </p>
        </div>
      </div>
    </main>
  );
}
