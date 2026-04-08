from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import AnalysisHistory
from app.schemas.analysis import AnalysisHistoryItem, StatsResponse

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history", response_model=list[AnalysisHistoryItem])
def get_history(db: Session = Depends(get_db)) -> list[AnalysisHistory]:
    return db.query(AnalysisHistory).order_by(desc(AnalysisHistory.created_at)).limit(20).all()


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)) -> StatsResponse:
    rows = db.query(AnalysisHistory).all()
    if not rows:
        return StatsResponse(
            total_analyses=0,
            average_score=0.0,
            most_common_formality="n/a",
            most_common_tone="n/a",
        )

    formality_counter = Counter(row.formality_level for row in rows)
    tone_counter = Counter(row.tone_label for row in rows)

    return StatsResponse(
        total_analyses=len(rows),
        average_score=round(sum(row.overall_score for row in rows) / len(rows), 1),
        most_common_formality=formality_counter.most_common(1)[0][0],
        most_common_tone=tone_counter.most_common(1)[0][0],
    )
