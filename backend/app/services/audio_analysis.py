"""
Audio deepfake analysis service.
Loads the CNN-BiLSTM model once at module level (singleton pattern,
mirrors how MesoNetDetector is used in websocket.py).

Expects: raw audio bytes (webm/wav from browser MediaRecorder)
Returns: dict with risk_score (0.0 = real, 1.0 = fake) + verdict
"""
from __future__ import annotations

import io
import logging
import os
import tempfile

import numpy as np

logger = logging.getLogger(__name__)

# ── Singleton ────────────────────────────────────────────────────────────────
_model = None
import pathlib
_MODEL_PATH = os.environ.get(
    "AUDIO_MODEL_PATH",
    str(pathlib.Path(__file__).parent.parent.parent / "ml" / "audio" / "audio_classifier.h5")
)


def get_audio_model():
    """Load the Keras model once and cache it (mirrors get_mesonet() pattern)."""
    global _model
    if _model is None:
        try:
            # Import here so the rest of the app starts even if TF isn't installed
            import tensorflow as tf  # type: ignore
            _model = tf.keras.models.load_model(_MODEL_PATH)
            logger.info("Audio CNN-BiLSTM model loaded from %s", _MODEL_PATH)
        except Exception as exc:
            logger.error("Failed to load audio model: %s", exc)
            _model = None
    return _model


# ── Preprocessing (mirrors processor.py exactly) ─────────────────────────────
def _prepare_audio_for_model(file_path: str, target_sr: int = 16000, duration: int = 5) -> np.ndarray:
    """
    Exact copy of your processor.py logic.
    Takes a file path, returns ndarray of shape (1, 128, 109, 1).
    """
    import librosa  # type: ignore

    audio, sr = librosa.load(file_path, sr=target_sr)

    # Tile instead of zero-pad (preserves natural frequency distribution)
    required_samples = target_sr * duration
    if len(audio) < required_samples:
        audio = np.resize(audio, required_samples)
    else:
        audio = audio[:required_samples]

    spectrogram = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=128)
    log_spectrogram = librosa.power_to_db(spectrogram)

    # Z-score normalization — prevents sigmoid saturation
    mean = np.mean(log_spectrogram)
    std = np.std(log_spectrogram)
    log_spectrogram = (log_spectrogram - mean) / (std + 1e-8)

    # Enforce exact shape (128, 109)
    max_frames = 109
    if log_spectrogram.shape[1] < max_frames:
        log_spectrogram = np.pad(
            log_spectrogram,
            ((0, 0), (0, max_frames - log_spectrogram.shape[1])),
        )
    else:
        log_spectrogram = log_spectrogram[:, :max_frames]

    # Shape: (1, 128, 109, 1) — batch + channel dims for CNN
    return log_spectrogram[np.newaxis, ..., np.newaxis]


# ── Public API ────────────────────────────────────────────────────────────────
def analyze_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Main entry point called by the WebSocket router.

    The browser sends raw MediaRecorder chunks (webm/opus by default).
    We write to a temp file so librosa can read it — this is the only
    adapter needed since processor.py expects a file path.

    Returns:
        {
            "risk_score": float,   # 0.0 = definitely real, 1.0 = definitely fake
            "verdict": str,        # "real" | "fake" | "suspicious"
            "confidence": float,   # same as risk_score, explicit for frontend
            "model_available": bool
        }
    """
    model = get_audio_model()

    if model is None:
        # Graceful degradation — don't crash the WS handler if model failed to load
        return {
            "risk_score": 0.0,
            "verdict": "unavailable",
            "confidence": 0.0,
            "model_available": False,
        }

    # Determine file suffix so librosa picks the right decoder
    suffix = ".webm" if "webm" in mime_type else ".wav"

    try:
        # Write bytes to a named temp file, run preprocessing, delete immediately
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        features = _prepare_audio_for_model(tmp_path)
        raw_score = float(model.predict(features, verbose=0)[0][0])

    except Exception as exc:
        logger.error("Audio inference error: %s", exc)
        return {
            "risk_score": 0.0,
            "verdict": "error",
            "confidence": 0.0,
            "model_available": True,
        }
    finally:
        # Always clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    verdict = _score_to_verdict(raw_score)

    return {
        "risk_score": raw_score,
        "verdict": verdict,
        "confidence": raw_score,
        "model_available": True,
    }


def _score_to_verdict(score: float) -> str:
    """
    Thresholds tuned for your saturated sigmoid behaviour.
    Since the model tends toward 0.0 or 1.0, the middle band
    catches edge cases / noisy audio.
    """
    if score >= 0.75:
        return "fake"
    elif score >= 0.45:
        return "suspicious"
    else:
        return "real"
