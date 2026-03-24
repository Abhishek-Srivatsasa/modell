"""
Audio deepfake detection WebSocket router.

Endpoint : ws/live-audio/{session_id}
Mirrors   : app/routers/websocket.py (video pipeline) — same manager,
            same result-throttle pattern, same DB write cadence.

Completely isolated — zero shared state with the video pipeline.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.websocket.manager import manager
from app.services.audio_analysis import analyze_audio_bytes

router = APIRouter()

# ── chunk tracking ────────────────────────────────────────────────────────────
# We accumulate incoming bytes until we have ~5 seconds worth,
# then run inference. MediaRecorder sends ~1s chunks by default,
# so we buffer 5 of them before each inference call.
_CHUNKS_PER_INFERENCE = 5


@router.websocket("/ws/live-audio/{session_id}")
async def websocket_audio_live(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Handle live audio stream for deepfake detection.

    Protocol (mirrors video WS):
    - Client sends raw audio bytes (MediaRecorder webm/opus chunks)
    - Server accumulates 5 chunks (~5 seconds) then runs CNN-BiLSTM inference
    - Server sends back risk_score + verdict JSON every ~5 seconds
    - DB write happens every 5 inferences (same cadence as video pipeline)
    """
    await manager.connect(websocket, session_id)

    chunk_buffer: list[bytes] = []
    chunk_count = 0
    inference_count = 0
    last_result_time = asyncio.get_event_loop().time()

    # Last known result — sent on every throttle tick even between inferences
    last_result: dict = {
        "audio_risk_score": 0.0,
        "audio_verdict": "pending",
        "audio_confidence": 0.0,
        "model_available": False,
        "chunk_count": 0,
        "inference_count": 0,
        "session_id": session_id,
    }

    try:
        while True:
            try:
                message = await websocket.receive()

                if message["type"] == "websocket.disconnect":
                    break

                # Accept binary audio chunks from MediaRecorder
                raw: bytes = message.get("bytes") or b""
                if not raw:
                    continue

                chunk_buffer.append(raw)
                chunk_count += 1

                # ── Run inference every N chunks (~5 seconds of audio) ────────
                if len(chunk_buffer) >= _CHUNKS_PER_INFERENCE:
                    combined = b"".join(chunk_buffer)
                    chunk_buffer = []  # reset buffer

                    # Run in thread pool — librosa + TF are blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, analyze_audio_bytes, combined, "audio/webm"
                    )

                    inference_count += 1
                    last_result = {
                        "audio_risk_score": result["risk_score"],
                        "audio_verdict": result["verdict"],
                        "audio_confidence": result["confidence"],
                        "model_available": result["model_available"],
                        "chunk_count": chunk_count,
                        "inference_count": inference_count,
                        "session_id": session_id,
                    }

                # ── Throttled send (mirrors 0.5s throttle in video WS) ───────
                now = asyncio.get_event_loop().time()
                if now - last_result_time >= 0.5:
                    try:
                        await manager.send_result(session_id, last_result)
                        last_result_time = now
                    except Exception:
                        break

            except Exception:
                break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, session_id)
