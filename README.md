# Tone Analyzer MVP

한국어 비즈니스 텍스트의 격식 수준, 톤, 일관성을 분석하는 초기 버전입니다.

## 기술 스택

- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite
- Frontend: React, TypeScript, Vite
- 분석: 규칙 기반 형태소/종결어미 추정기, 톤/높임법 휴리스틱
- AI 보강: OpenAI Responses API

## 현재 제공 기능

- 텍스트 전체 분석: 격식 수준, 톤, 품질 점수
- 문장 단위 일관성 점검
- 문제 하이라이트 데이터 반환
- 분석 이력 저장 및 최근 분석 조회
- OpenAI 기반 문장 개선 제안 생성
- 간단한 통계 API

## 실행 방법

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

`.env`는 `backend/.env`에 두고 사용합니다. 예시는 `backend/.env.example`에 있습니다.
`.env.example`을 복사해서 `.env`를 만들고  `LLM_API_KEY` 부분에 AI API를 적어 넣으면 됩니다. 

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

기본 주소:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

