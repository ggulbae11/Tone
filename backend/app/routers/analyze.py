from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import AnalysisHistory
from app.schemas.analysis import AnalyzeRequest, FullAnalysisResponse, RewritePlanRequest, RewritePlanResponse
from app.services.analyzer_service import AnalyzerService

router = APIRouter(prefix="/api", tags=["analyze"])
service = AnalyzerService()


@router.post("/analyze/full", response_model=FullAnalysisResponse)
def analyze_full(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> FullAnalysisResponse:
    result = service.analyze_full(payload.text)

    history_item = AnalysisHistory(
        input_text=payload.text,
        overall_score=result.overall_score,
        formality_level=result.formality_level,
        tone_label=result.tone_label,
        issue_count=len(result.issues),
        result_payload=result.model_dump(),
    )
    db.add(history_item)
    db.commit()

    return result


@router.post("/analyze/rewrite-plan", response_model=RewritePlanResponse)
def rewrite_plan(payload: RewritePlanRequest) -> RewritePlanResponse:
    return service.create_rewrite_plan(payload.text, payload.target_level)


@router.post("/analyze/formality")
def analyze_formality(payload: AnalyzeRequest) -> dict:
    result = service.analyze_full(payload.text)
    return {
        "formality_level": result.formality_level,
        "formality_score": result.formality_score,
        "distribution": result.endings_distribution,
        "sentences": result.sentences,
    }


@router.post("/analyze/tone")
def analyze_tone(payload: AnalyzeRequest) -> dict:
    result = service.analyze_full(payload.text)
    return {
        "tone_label": result.tone_label,
        "tone_confidence": result.tone_confidence,
        "summary": result.summary,
    }


@router.post("/analyze/consistency")
def analyze_consistency(payload: AnalyzeRequest) -> dict:
    result = service.analyze_full(payload.text)
    return {
        "consistency_score": result.consistency_score,
        "issues": result.issues,
        "highlights": result.highlights,
    }