from __future__ import annotations
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, func, text
from sqlalchemy import String
from sqlalchemy.types import DateTime

from db.database import Base


class VerificationSession(Base):
    """Verification session representing a single identity verification attempt."""

    __tablename__ = "verification_sessions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: __import__("uuid").uuid4().hex,
        nullable=False,
    )
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    mode = Column(String, nullable=False)  # live | upload
    status = Column(String, nullable=False, server_default=text("'pending'"))
    subject_name = Column(String, nullable=True)
    media_path = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"VerificationSession(id={self.id!r}, user_id={self.user_id!r})"

