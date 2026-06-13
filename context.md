# Hand Gesture Recognition Platform — Project Context

> **Purpose**: This file tracks the full project prompt, what has been built, and what remains.
> Read this first before touching any code to avoid re-scanning the entire codebase.

---

## Original Prompt Summary

Build a complete production-ready Hand Gesture Recognition system:

- **AI**: TensorFlow/Keras CNN + MobileNetV2 + EfficientNetB0, MediaPipe for 21-landmark extraction
- **Dataset**: LeapGestRecog (Kaggle) — ~20,000 images, 10 gesture classes
  - Palm, L, Fist, Fist Moved, Thumb, Index, OK, Palm Moved, C, Down
- **Backend**: FastAPI — JWT auth, predict, retrain, health, metrics, Prometheus
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Database**: PostgreSQL (SQLAlchemy ORM + Alembic migrations)
- **Deployment**: Vercel (frontend), Render/Railway (backend), Neon/Supabase (DB)
- **DevOps**: Docker optional, GitHub Actions CI/CD
- **Security**: JWT, bcrypt, rate limiting, CORS, env secrets
- **Testing**: pytest, 80%+ coverage

---

## Project Root

```
g:\Hand_Gestre_Rec\
```

---

## Architecture

```
React Frontend (Vercel)
       ↓
FastAPI Backend (Render/Railway)
       ↓
PostgreSQL (Neon/Supabase)
       ↓
TensorFlow Gesture Recognition Model
```

---

## ✅ COMPLETED — What Already Exists

### AI Pipeline (`ai/`)
- [x] `ai/__init__.py`
- [x] `ai/download_dataset.py` — Kaggle dataset downloader
- [x] `ai/augment.py` — data augmentation pipeline
- [x] `ai/train.py` — full training pipeline (CNN, MobileNetV2, EfficientNetB0), early stopping, checkpointing, TensorBoard, confusion matrix, classification report
- [x] `ai/evaluate.py` — model evaluation
- [x] `ai/inference.py` — `GesturePredictor` class, image + landmark modes, base64 support, MediaPipe integration, singleton thread-safe

### Backend Core (`backend/core/`)
- [x] `backend/__init__.py`
- [x] `backend/core/__init__.py`
- [x] `backend/core/config.py` — Pydantic Settings (DATABASE_URL, SECRET_KEY, JWT config, CORS, inference config)
- [x] `backend/core/security.py` — bcrypt password hashing, JWT create/decode, FastAPI dependencies (get_current_user, get_admin_user)
- [x] `backend/core/logging.py` — structured logging setup

### Backend Database (`backend/db/`)
- [x] `backend/db/__init__.py`
- [x] `backend/db/database.py` — SQLAlchemy engine, SessionLocal, Base, get_db() dependency, init_db()

### Backend Stubs (empty `__init__.py` only)
- [x] `backend/routers/__init__.py` — EMPTY (needs routes)
- [x] `backend/schemas/__init__.py` — EMPTY (needs schemas)

### Frontend Pages (`frontend/src/pages/`)
- [x] `frontend/src/pages/Hero.tsx` — landing page with video background, nav, CTA
- [x] `frontend/src/pages/Login.tsx` — login form with JWT auth, error handling
- [x] `frontend/src/pages/Register.tsx` — register form with password strength indicator
- [x] `frontend/src/pages/Dashboard.tsx` — full dashboard UI (webcam + gesture overlay + confidence bars + history + stats chart + admin panel)

### Frontend Root
- [x] `frontend/src/App.tsx` — React Router setup, ProtectedRoute, AuthProvider
- [x] `frontend/src/main.tsx`
- [x] `frontend/src/index.css`
- [x] `frontend/index.html`
- [x] `frontend/package.json` — React 18, react-router-dom, axios, recharts, lucide-react, Tailwind
- [x] `frontend/vite.config.ts`
- [x] `frontend/tsconfig.json`
- [x] `frontend/tailwind.config.cjs`
- [x] `frontend/postcss.config.js`
- [x] `frontend/vercel.json`

### Root Config
- [x] `.env.example`
- [x] `requirements.txt`
- [x] `alembic.ini`
- [x] `render.yaml`
- [x] `railway.toml`
- [x] `tests/__init__.py` — EMPTY

---

## ❌ MISSING — What Needs To Be Built

### Backend Models (`backend/models/`) — ALL MISSING
- [x] `backend/models/__init__.py`
- [x] `backend/models/user.py` — User ORM (id, email, username, hashed_password, is_admin, is_active, created_at)
- [x] `backend/models/prediction.py` — Prediction log (id, user_id, gesture, confidence, mode, timestamp)
- [x] `backend/models/training.py` — TrainingJob (id, user_id, status, backbone, epochs, accuracy, loss, started_at, finished_at)
- [x] `backend/models/audit.py` — AuditLog (id, user_id, action, detail, ip_address, created_at)

### Backend Schemas (`backend/schemas/`) — ALL MISSING
- [x] `backend/schemas/__init__.py`
- [x] `backend/schemas/auth.py` — LoginRequest, RegisterRequest, TokenResponse, RefreshRequest, UserOut
- [x] `backend/schemas/prediction.py` — PredictRequest (base64/landmarks), PredictResponse (gesture, confidence, allScores, mode, inferenceMs), HistoryItem, HistoryOut
- [x] `backend/schemas/training.py` — TrainRequest (backbone, epochs, batch_size), TrainStatusOut, TrainHistoryOut
- [x] `backend/schemas/admin.py` — StatsOut, UserListOut, UserAdminOut

### Backend Routers (`backend/routers/`) — ALL MISSING
- [x] `backend/routers/__init__.py`
- [x] `backend/routers/auth.py` — POST /auth/register, POST /auth/login, POST /auth/refresh, GET /auth/me
- [x] `backend/routers/predict.py` — POST /predict (base64 image → gesture + confidence + all_scores)
- [x] `backend/routers/training.py` — POST /training/start, GET /training/status/{id}, GET /training/history
- [x] `backend/routers/admin.py` — GET /admin/stats, GET /admin/users, DELETE /admin/users/{id}

### Backend Main App — MISSING
- [x] `backend/main.py` — FastAPI app, CORS, SlowAPI rate limiting, router registration, startup (init_db, load model), /health, /metrics, Prometheus

### Frontend Hooks (`frontend/src/hooks/`) — ALL MISSING
- [x] `frontend/src/hooks/useAuth.tsx` — React context: user, login(), register(), logout(), isAuthenticated, isLoading; JWT in localStorage; axios interceptor
- [x] `frontend/src/hooks/useWebcam.ts` — getUserMedia, startCamera(), stopCamera(), captureFrame() → base64
- [x] `frontend/src/hooks/usePrediction.ts` — sendPrediction(base64), currentPrediction, history[], fps, isProcessing

### Frontend Components (`frontend/src/components/`) — ALL MISSING
- [x] `frontend/src/components/Webcam.tsx` — video element with start/stop button, camera toggle
- [x] `frontend/src/components/GestureOverlay.tsx` — floating gesture name + confidence badge on video
- [x] `frontend/src/components/ConfidenceBar.tsx` — horizontal bar chart per gesture class
- [x] `frontend/src/components/PredictionHistory.tsx` — scrollable list of past predictions
- [x] `frontend/src/components/StatsChart.tsx` — Recharts BarChart of gesture frequency counts
- [x] `frontend/src/components/AdminPanel.tsx` — admin controls: trigger training, view training jobs, user list

### Frontend API Client — MISSING
- [x] `frontend/src/api/client.ts` — Axios instance (VITE_API_URL), Bearer token interceptor, refresh token logic

### Alembic Migrations — MISSING
- [x] `alembic/` directory with `env.py`, versions/
- [x] Initial migration for users, predictions, training_jobs, audit_logs

### Testing (`tests/`) — ALL MISSING
- [x] `tests/conftest.py` — pytest fixtures (test DB, test client, auth headers)
- [x] `tests/test_auth.py` — register, login, refresh, me endpoint tests
- [x] `tests/test_predict.py` — predict endpoint tests
- [x] `tests/test_training.py` — training trigger + status tests
- [x] `tests/test_inference.py` — unit tests for GesturePredictor

### Docker — MISSING
- [x] `docker/Dockerfile.backend`
- [x] `docker/Dockerfile.frontend`
- [x] `docker-compose.yml`

### CI/CD — MISSING
- [x] `.github/workflows/backend.yml`
- [x] `.github/workflows/frontend.yml`
- [x] `.github/workflows/deploy.yml`

### Documentation — MISSING
- [x] `README.md`

---

## Implementation Order

1. **Backend Models** → schemas → routers → main.py  (backend is the blocker)
2. **Frontend API client** → hooks → components  (unblocks the entire frontend)
3. **Alembic migrations**
4. **Tests**
5. **Docker + CI/CD**
6. **README**

---

## Key Design Decisions

| Decision | Choice |
|---|---|
| DB default | SQLite for dev, PostgreSQL for prod (both supported via DATABASE_URL) |
| Auth | JWT (access 30min, refresh 7d) stored in localStorage |
| Inference mode | `image` by default; `landmark` via env var |
| Model | CNN by default; MobileNetV2/EfficientNetB0 via config |
| Rate limiting | SlowAPI (100 req/min on predict endpoint) |
| Frontend deploy | Vercel |
| Backend deploy | Render (primary) or Railway |
| DB cloud | Neon or Supabase (PostgreSQL) |

---

## File: Key API Contracts

### POST /auth/login
```json
Request:  { "email": "str", "password": "str" }
Response: { "access_token": "str", "refresh_token": "str", "token_type": "bearer", "user": {...} }
```

### POST /predict
```json
Request:  { "image": "base64str", "mode": "image|landmark" }
Response: { "gesture": "Palm", "confidence": 0.97, "all_scores": {...}, "inference_ms": 45.2 }
```

### POST /training/start
```json
Request:  { "backbone": "cnn", "epochs": 50, "batch_size": 32 }
Response: { "job_id": "uuid", "status": "queued" }
```

---

## Notes for Future Sessions

- `Dashboard.tsx` is fully wired — it just needs the hooks/components to exist
- `inference.py` handles both image and landmark modes with a clean singleton API
- `train.py` is complete — the API just needs to call it in a background thread
- SQLite works out of the box for dev; just set DATABASE_URL to postgres for prod
- The frontend already uses Tailwind — no additional CSS framework needed
- `alembic.ini` exists but the `alembic/` directory with migrations does NOT exist yet
