from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    input_text: Mapped[str] = mapped_column(Text)
    overall_score: Mapped[float] = mapped_column(Float)
    formality_level: Mapped[str] = mapped_column(String(50))
    tone_label: Mapped[str] = mapped_column(String(50))
    issue_count: Mapped[int] = mapped_column(Integer, default=0)
    result_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

