from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from app.models import DetectionResult, VerificationSession, FrameResult
from app.schemas.verification import DetectionResultSchema, StartLiveSessionRequest
from app.services.risk_scoring import RiskScorer
from app.services.storage import MEDIA_BUCKET, MinioStorageService
from ml.mock_service import MockXceptionDetector
from workers.celery_app import app as celery_app


router = APIRouter()
TEST_USER_ID = UUID("da11c5eb-1d2e-417e-98fd-ff1369ef24ce")

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "video/mp4",
    "video/webm",
    "audio/wav",
    "audio/mpeg",
}


@router.post("/upload")
async def upload_verification_media(
    file: UploadFile = File(...),
    detection_mode: str = Form(default="faceswap"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Upload media, create a verification session, trigger async analysis."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported media type.")

    object_key = f"{uuid4()}/{file.filename}"

    now = datetime.now(timezone.utc)
    session = VerificationSession(
        user_id=str(TEST_USER_ID),
        mode="upload",
        status="complete",
        subject_name=None,
        media_path=object_key,
        started_at=now,
        completed_at=now,
        duration_seconds=1,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Run actual analysis locally (bypassing Minio/Celery but keeping real models)
    import tempfile
    import os
    import cv2
    import numpy as np
    
    frames = []
    contents = await file.read()
    if file.content_type.startswith("video/"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_file.write(contents)
            temp_file_path = temp_file.name
        cap = cv2.VideoCapture(temp_file_path)
        for _ in range(15):
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
            else:
                break
        cap.release()
        os.remove(temp_file_path)
    else:
        np_arr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is not None:
            frames = [img] * 15  # Duplicate frame to simulate 15-frame buffer for rPPG

    from ml.deepfake.mesonet import MesoNetDetector
    from ml.deepfake.gradcam import MesoNetGradCAM
    from ml.liveness.rppg_extractor import RPPGExtractor
    import base64
    import io
    from PIL import Image as PILImage

    scorer = RiskScorer()
    mesonet = MesoNetDetector()
    rppg = RPPGExtractor()
    
    for f in frames:
        rppg.add_frame(f)
    bpm_data = rppg.compute_bpm()

    mesonet_score = 0.0
    gradcam_base64 = None
    suspicious_regions_list = []
    
    if file.content_type.startswith("audio/"):
        from app.services.audio_analysis import analyze_audio_bytes
        audio_result = analyze_audio_bytes(contents, getattr(file, "content_type", "audio/wav"))
        
        signals = {
            "xception_score": 0.5,
            "temporal_consistency": 0.5,
            "rppg_score": 0.5,
            "liveness_score": 0.5,
            "audio_score": audio_result.get("risk_score", 0.0)
        }
        # Fake a quick risk map
        risk = scorer.compute_risk(signals)
        bpm_data = {"bpm": 0.0}
    else:
        if frames:
            prediction = mesonet.predict_frame(frames[0])
            mesonet_score = float(prediction.get("score", 0.0))
            
            try:
                _gradcam = MesoNetGradCAM(mesonet)
                target_f = getattr(mesonet, "last_cropped_face", frames[0])
                if target_f is None: target_f = frames[0]
                gradcam_result = _gradcam.analyze(target_f)
                if gradcam_result.get("overlay") is not None:
                    pil_img = PILImage.fromarray(gradcam_result["overlay"])
                    buffer = io.BytesIO()
                    pil_img.save(buffer, format="JPEG")
                    gradcam_base64 = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()
                if gradcam_result.get("suspicious_regions"):
                    suspicious_regions_list = gradcam_result["suspicious_regions"]
            except Exception:
                pass

        signals = {
            "xception_score": max(0.0, 1.0 - mesonet_score),
            "temporal_consistency": 0.8,
            "rppg_score": bpm_data.get("liveness_score", 0.5),
            "liveness_score": 0.8,
            "audio_score": 0.5,
        }
        risk = scorer.compute_risk(signals)

    det = DetectionResult(
        session_id=str(session.id),
        verdict=risk.verdict,
        risk_score=risk.risk_score,
        risk_level=risk.risk_level,
        xception_score=signals["xception_score"],
        temporal_score=signals["temporal_consistency"],
        rppg_score=signals["rppg_score"],
        liveness_score=signals["liveness_score"],
        audio_score=signals["audio_score"],
        suspicious_regions=suspicious_regions_list,
        gradcam_path=gradcam_base64,
        explanation_reasons=risk.explanation_reasons,
        confidence_interval=risk.confidence_interval,
        created_at=now,
    )
    db.add(det)
    
    for i in range(15):
        fr = FrameResult(
            session_id=str(session.id),
            frame_number=i + 1,
            timestamp_ms=(i + 1) * 33,
            xception_score=signals["xception_score"],
            temporal_consistency=0.8,
            rppg_value=float(bpm_data.get("bpm", 0.0)),
            is_flagged=False,
            created_at=now,
        )
        db.add(fr)

    await db.commit()

    return {"session_id": str(session.id), "status": "pending"}


@router.post("/start-live")
async def start_live_session(
    payload: StartLiveSessionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Create a live verification session and return websocket URL."""
    session = VerificationSession(
        user_id=str(TEST_USER_ID),
        mode="live",
        status="pending",
        subject_name=payload.subject_name,
        media_path=None,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    websocket_url = f"ws://127.0.0.1:8000/ws/live/{session.id}"
    return {"session_id": str(session.id), "websocket_url": websocket_url}


@router.delete("/end-live/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_live_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Mark a live session as complete and set duration."""
    result = await db.execute(select(VerificationSession).where(VerificationSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    now = datetime.now(timezone.utc)
    session.status = "complete"
    session.completed_at = now
    if session.started_at is not None:
        session.duration_seconds = int((now - session.started_at).total_seconds())
    await db.commit()
    from workers.tasks.video_analysis import analyze_video_task

    analyze_video_task.delay(str(session_id), "")


@router.post("/sync", response_model=DetectionResultSchema)
async def sync_verification(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
) -> DetectionResultSchema:
    """Run synchronous mock detection, persist result, and return it."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported media type.")

    x_model = MockXceptionDetector()
    scorer = RiskScorer()

    prediction = x_model.predict_frame(None)
    x_score = float(prediction["score"])

    signals = {
        "xception_score": x_score,
        "temporal_consistency": 0.5,
        "rppg_score": 0.5,
        "liveness_score": 0.5,
        "audio_score": 0.5,
    }
    risk = scorer.compute_risk(signals)

    now = datetime.now(timezone.utc)
    session = VerificationSession(
        user_id=str(TEST_USER_ID),
        mode="upload",
        status="complete",
        subject_name=None,
        media_path=None,
        started_at=now,
        completed_at=now,
        duration_seconds=0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    det = DetectionResult(
        session_id=session.id,
        verdict=risk.verdict,
        risk_score=risk.risk_score,
        risk_level=risk.risk_level,
        xception_score=signals["xception_score"],
        temporal_score=signals["temporal_consistency"],
        rppg_score=signals["rppg_score"],
        liveness_score=signals["liveness_score"],
        audio_score=signals["audio_score"],
        gradcam_path=None,
        suspicious_regions=None,
        explanation_reasons=risk.explanation_reasons,
        confidence_interval=risk.confidence_interval,
        created_at=now,
    )
    db.add(det)
    await db.commit()
    await db.refresh(det)

    return DetectionResultSchema.model_validate(det)

