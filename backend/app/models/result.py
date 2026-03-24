from __future__ import annotations
import uuid

from sqlalchemy import Boolean, Column, Float, ForeignKey, String, func, text
from sqlalchemy import JSON as JSONB, String
from sqlalchemy import JSON as ARRAY
from sqlalchemy.types import DateTime, Integer

from db.database import Base


class DetectionResult(Base):
    """Aggregated detection result for a verification session."""

    __tablename__ = "detection_results"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: __import__("uuid").uuid4().hex,
        nullable=False,
    )
    session_id = Column(String(36), ForeignKey("verification_sessions.id"), nullable=False, index=True)
    verdict = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    xception_score = Column(Float, nullable=True)
    temporal_score = Column(Float, nullable=True)
    rppg_score = Column(Float, nullable=True)
    liveness_score = Column(Float, nullable=True)
    audio_score = Column(Float, nullable=True)
    gradcam_path = Column(String, nullable=True)
    suspicious_regions = Column(JSONB, nullable=True)
    explanation_reasons = Column(ARRAY(String), nullable=True)
    confidence_interval = Column(ARRAY(Float), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"DetectionResult(id={self.id!r}, verdict={self.verdict!r}, risk_score={self.risk_score!r})"


class FrameResult(Base):
    """Per-frame detection metrics for a verification session."""

    __tablename__ = "frame_results"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: __import__("uuid").uuid4().hex,
        nullable=False,
    )
    session_id = Column(String(36), ForeignKey("verification_sessions.id"), nullable=False, index=True)
    frame_number = Column(Integer, nullable=False)
    timestamp_ms = Column(Integer, nullable=False)
    xception_score = Column(Float, nullable=True)
    temporal_consistency = Column(Float, nullable=True)
    rppg_value = Column(Float, nullable=True)
    is_flagged = Column(Boolean, nullable=False, server_default=text("FALSE"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"FrameResult(id={self.id!r}, session_id={self.session_id!r}, frame_number={self.frame_number!r})"