from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import AnalysisHistory
from app.schemas.analysis import (
    AnalyzeSentencesRequest,
    ContextOnlyResponse,
    ExtractContextRequest,
    FullAnalysisResponse,
)
from app.services.analyzer_service import AnalyzerService

router = APIRouter(prefix="/api", tags=["analyze"])
service = AnalyzerService()


@router.post("/analyze/context", response_model=ContextOnlyResponse)
def extract_context(payload: ExtractContextRequest) -> ContextOnlyResponse:
    """1단계: 원문에서 맥락 요소만 추출"""
    return service.extract_context(payload.text)


@router.post("/analyze/sentences", response_model=FullAnalysisResponse)
def analyze_sentences(
    payload: AnalyzeSentencesRequest,
    db: Session = Depends(get_db),
) -> FullAnalysisResponse:
    """2단계: 사용자가 확인·수정한 맥락으로 문장 분석"""
    result = service.analyze_sentences(
        text=payload.text,
        context_values=payload.context_values,
        overall_summary=payload.overall_summary,
        implicit_style_value=payload.implicit_style_value,
    )

    context_dict = {f.key: f.value for f in result.context.factors}
    db.add(AnalysisHistory(
        input_text=payload.text,
        overall_score=result.overall_score,
        formality_level=context_dict.get("formality_expected", "파악 불가"),
        tone_label=context_dict.get("situation", "파악 불가"),
        issue_count=result.inconsistent_count + result.flow_issue_count + result.implicit_style_issue_count,
        result_payload=result.model_dump(),
    ))
    db.commit()

    return result
