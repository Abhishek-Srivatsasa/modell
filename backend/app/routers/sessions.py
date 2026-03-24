from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import and_, func, select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db_session
from app.models import DetectionResult, FrameResult, VerificationSession
from app.schemas.session import DashboardStatsSchema, FrameResultSchema, SessionListResponse, SessionSchema
from app.services.storage import HEATMAP_BUCKET, MinioStorageService


router = APIRouter()


@router.get("/", response_model=None)
async def list_sessions(
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[str] = None,
    mode: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Return paginated list of sessions with optional filters."""
    query = select(VerificationSession)
    if status_filter:
        query = query.where(VerificationSession.status == status_filter)
    if mode:
        query = query.where(VerificationSession.mode == mode)

    total = (await db.execute(
        query.with_only_columns(func.count())
    )).scalar_one()

    sessions = (await db.execute(
        query.order_by(VerificationSession.started_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )).scalars().all()

    # Get detection results for all sessions
    session_ids = [s.id for s in sessions]
    det_results = {}
    if session_ids:
        dets = (await db.execute(
            select(DetectionResult).where(
                DetectionResult.session_id.in_(session_ids)
            )
        )).scalars().all()
        det_results = {d.session_id: d for d in dets}

    items = []
    for s in sessions:
        det = det_results.get(s.id)
        # Extract filename from media_path
        filename = None
        if s.media_path:
            filename = s.media_path.split("/")[-1]
        
        # Calculate duration
        duration = None
        if s.started_at and s.completed_at:
            duration = round((s.completed_at - s.started_at).total_seconds(), 1)
        
        items.append({
            "id": str(s.id),
            "mode": s.mode,
            "status": s.status,
            "subject_name": s.subject_name or filename or "Unknown",
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "duration_seconds": duration,
            "risk_score": det.risk_score if det else None,
            "verdict": det.verdict if det else None,
            "risk_level": det.risk_level if det else None,
        })

    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/{session_id}")
async def get_session_detail(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return session, detection_result, and frame_results."""
    result = await db.execute(select(VerificationSession).where(VerificationSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    det = (
        await db.execute(select(DetectionResult).where(DetectionResult.session_id == session_id))
    ).scalar_one_or_none()
    frame_results = (
        await db.execute(select(FrameResult).where(FrameResult.session_id == session_id).order_by(FrameResult.id))
    ).scalars().all()

    return {
        "id": str(session.id),
        "user_id": str(session.user_id),
        "mode": session.mode,
        "status": session.status,
        "subject_name": session.subject_name,
        "media_path": session.media_path,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "duration_seconds": session.duration_seconds,
        "heatmap_url": det.gradcam_path if det and det.gradcam_path else None,
        "result": {
            "verdict": det.verdict,
            "risk_score": det.risk_score,
            "risk_level": det.risk_level,
            "xception_score": det.xception_score,
            "temporal_score": det.temporal_score,
            "rppg_score": det.rppg_score,
            "rppg_bpm": frame_results[-1].rppg_value if frame_results and frame_results[-1].rppg_value is not None else 0.0,
            "liveness_score": det.liveness_score,
            "audio_score": det.audio_score,
            "explanation_reasons": det.explanation_reasons,
            "suspicious_regions": det.suspicious_regions,
            "confidence_interval": det.confidence_interval,
            "gradcam_path": det.gradcam_path,
        }
        if det
        else None,
        "frame_results": [
            {
                "frame_number": f.frame_number,
                "timestamp_ms": f.timestamp_ms,
                "xception_score": f.xception_score,
                "temporal_consistency": f.temporal_consistency,
                "rppg_value": f.rppg_value,
                "is_flagged": f.is_flagged,
            }
            for f in frame_results
        ],
    }


@router.get("/{session_id}/heatmap")
async def get_session_heatmap(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Return Grad-CAM heatmap image from MinIO."""
    det = (
        await db.execute(select(DetectionResult).where(DetectionResult.session_id == session_id))
    ).scalar_one_or_none()
    if det is None or not det.gradcam_path:
        raise HTTPException(status_code=404, detail="Heatmap not found.")

    storage = MinioStorageService()
    data = storage.download_file(HEATMAP_BUCKET, det.gradcam_path)
    return StreamingResponse(iter([data]), media_type="image/png")


@router.get("/{session_id}/report")
async def get_session_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Return a placeholder PDF report."""
    content = b"%PDF-1.4\n% Pratyaksha report placeholder\n"
    return Response(content=content, media_type="application/pdf")


@router.delete("/{session_id}")
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    await db.execute(
        sql_delete(DetectionResult).where(
            DetectionResult.session_id == session_id
        )
    )
    await db.execute(
        sql_delete(FrameResult).where(
            FrameResult.session_id == session_id
        )
    )
    result = await db.execute(
        select(VerificationSession).where(
            VerificationSession.id == session_id
        )
    )
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
    await db.commit()
    return {"deleted": True}

