from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers.analyze import router as analyze_router
from app.routers.history import router as history_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="한국어 비즈니스 텍스트의 격식, 톤, 일관성을 분석하는 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(history_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "environment": settings.app_env}
