"use client";

import { useEffect, useMemo, useState } from "react";

import HeatmapViewer from "@/components/analysis/HeatmapViewer";
import SignalPanel from "@/components/verification/SignalPanel";
import { getSession, uploadMedia } from "@/lib/api";
import { LiveDetectionResult, SuspiciousRegion } from "@/lib/live-types";

const ACCEPTED_TYPES = [
  "image/jpeg",
  "image/png",
  "video/mp4",
  "video/webm",
  "audio/wav",
  "audio/mpeg",
];

const MAX_SIZE = 100 * 1024 * 1024;

const STEPS = [
  "Uploaded",
  "Queued",
  "Frame Extraction",
  "Face Analysis",
  "Audio Analysis",
  "Temporal Check",
  "Risk Fusion",
  "Report Ready",
];

function inferStep(status: string): number {
  const s = status.toLowerCase();
  if (s.includes("queued")) return 1;
  if (s.includes("extract")) return 2;
  if (s.includes("face")) return 3;
  if (s.includes("audio")) return 4;
  if (s.includes("temporal")) return 5;
  if (s.includes("fusion")) return 6;
  if (s.includes("complete") || s.includes("ready")) return 7;
  return 0;
}

export default function UploadAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [detectionMode, setDetectionMode] = useState<'faceswap' | 'aigenerated'>('faceswap');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<Record<string, unknown> | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const isComplete = status.toLowerCase().includes("complete") || status.toLowerCase().includes("ready");
  const currentStep = useMemo(() => inferStep(status), [status]);

  function validate(candidate: File): string | null {
    if (!ACCEPTED_TYPES.includes(candidate.type)) return "Unsupported file type.";
    if (candidate.size > MAX_SIZE) return "File must be smaller than 100MB.";
    return null;
  }

  function onFilePicked(candidate: File) {
    const validationError = validate(candidate);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setFile(candidate);
    setPreviewUrl(URL.createObjectURL(candidate));
  }

  async function handleUpload() {
    if (!file) return;
    setError(null);
    try {
      const response = await uploadMedia(file, detectionMode);
      setSessionId(response.session_id);
      setStatus(response.status ?? "queued");
    } catch {
      setError("Upload failed. Please retry.");
    }
  }

  useEffect(() => {
    if (!sessionId || isComplete) return;
    const timer = window.setInterval(async () => {
      try {
        const data = (await getSession(sessionId)) as Record<string, unknown>;
        setSessionData(data);
        const newStatus = String(data.status ?? status);
        setStatus(newStatus);
      } catch {
        // polling is best effort
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [isComplete, sessionId, status]);

  const liveLikeResult: LiveDetectionResult | null = sessionData
    ? {
        risk_score: Number((sessionData.result as any)?.risk_score ?? sessionData.risk_score ?? 0),
        xception_score: Number((sessionData.result as any)?.xception_score ?? sessionData.xception_score ?? 0),
        rppg_bpm: Number((sessionData.result as any)?.rppg_bpm ?? sessionData.rppg_bpm ?? 0),
        temporal_score: Number((sessionData.result as any)?.temporal_score ?? sessionData.temporal_score ?? 0),
        audio_spoof_probability: Number((sessionData.result as any)?.audio_score ?? sessionData.audio_score ?? 0),
        audio_attack_type: String((sessionData.result as any)?.audio_attack_type ?? sessionData.audio_attack_type ?? "NONE") as LiveDetectionResult["audio_attack_type"],
      }
    : null;

  const regions = (((sessionData?.result as any)?.suspicious_regions ?? sessionData?.suspicious_regions) as SuspiciousRegion[]) ?? [];
  const imageUrl = String(sessionData?.image_url ?? previewUrl ?? "");
  const heatmapUrl = String(sessionData?.heatmap_url ?? "");

  return (
    <div className="space-y-4">
      <h1 className="font-display text-xl text-text-primary">Upload Analysis</h1>
      <div className="flex gap-3 mb-6">
        <button
          onClick={() => setDetectionMode('faceswap')}
          className={`flex-1 p-4 rounded-lg border-2 transition-all cursor-pointer ${
            detectionMode === 'faceswap' 
              ? 'border-[#00D4FF] bg-[#00D4FF]/10 text-[#00D4FF]' 
              : 'border-[#1F2937] text-[#6B7280] hover:border-[#374151]'
          }`}
        >
          <div className="text-2xl mb-1">🎭</div>
          <div className="font-semibold">Face Swap Detection</div>
          <div className="text-xs mt-1">Neural face swaps, identity substitution in KYC calls</div>
          <div className="text-xs mt-2 font-mono opacity-70">MesoNet Meso4 • FaceForensics++</div>
        </button>
        <button
          onClick={() => setDetectionMode('aigenerated')}
          className={`flex-1 p-4 rounded-lg border-2 transition-all cursor-pointer ${
            detectionMode === 'aigenerated' 
              ? 'border-[#00D4FF] bg-[#00D4FF]/10 text-[#00D4FF]' 
              : 'border-[#1F2937] text-[#6B7280] hover:border-[#374151]'
          }`}
        >
          <div className="text-2xl mb-1">🤖</div>
          <div className="font-semibold">AI Generated Detection</div>
          <div className="text-xs mt-1">StyleGAN, Midjourney, DALL-E, Gemini synthetic faces</div>
          <div className="text-xs mt-2 font-mono opacity-70">CNN Classifier • HuggingFace</div>
        </button>
      </div>
      <div
        className="rounded-xl border border-dashed border-bg-border bg-bg-surface/60 p-6"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const dropped = e.dataTransfer.files?.[0];
          if (dropped) onFilePicked(dropped);
        }}
      >
        <p className="text-sm text-text-muted">Drag & drop JPG, PNG, MP4, WebM, WAV, MP3 (max 100MB)</p>
        <input
          type="file"
          accept=".jpg,.jpeg,.png,.mp4,.webm,.wav,.mp3"
          className="mt-3 block text-xs text-text-primary"
          onChange={(e) => {
            const picked = e.target.files?.[0];
            if (picked) onFilePicked(picked);
          }}
        />
        {previewUrl && file?.type.startsWith("image/") && <img src={previewUrl} alt="preview" className="mt-3 max-h-56 rounded" />}
        {previewUrl && file?.type.startsWith("video/") && <video src={previewUrl} controls className="mt-3 max-h-56 rounded" />}
        {previewUrl && file?.type.startsWith("audio/") && <audio src={previewUrl} controls className="mt-3 w-full" />}
        <button onClick={handleUpload} disabled={!file} className="mt-4 rounded bg-accent-cyan px-4 py-2 text-sm font-medium text-bg-base disabled:opacity-50">
          Upload & Analyze
        </button>
      </div>

      {error && <div className="rounded border border-danger/50 bg-danger/10 p-3 text-sm text-danger">{error}</div>}

      {sessionId && (
        <div className="rounded-xl border border-bg-border bg-bg-surface/60 p-4">
          <div className="mb-3 font-mono text-xs text-text-muted">Session {sessionId}</div>
          <div className="space-y-2">
            {STEPS.map((step, idx) => {
              const done = idx < currentStep;
              const active = idx === currentStep && !isComplete;
              return (
                <div key={step} className="flex items-center gap-2 text-sm">
                  <span className={done ? "text-safe" : active ? "animate-spin text-warning" : "text-text-muted"}>
                    {done ? "✓" : active ? "⟳" : "○"}
                  </span>
                  <span className={done ? "text-text-primary" : "text-text-muted"}>{step}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {isComplete && imageUrl && (
        <>
          <HeatmapViewer sessionId={sessionId ?? "unknown"} imageUrl={imageUrl} heatmapUrl={heatmapUrl || undefined} suspiciousRegions={regions} />
          <SignalPanel result={liveLikeResult} />
        </>
      )}
    </div>
  );
}
