# 🤙 Hand Gesture Recognition Platform

> AI-powered real-time hand gesture classification using TensorFlow, MediaPipe, FastAPI, and React.

[![Backend CI](https://github.com/your-username/hand-gesture-recognition/actions/workflows/backend.yml/badge.svg)](https://github.com/your-username/hand-gesture-recognition/actions)
[![Frontend CI](https://github.com/your-username/hand-gesture-recognition/actions/workflows/frontend.yml/badge.svg)](https://github.com/your-username/hand-gesture-recognition/actions)

---

## ✨ Features

- **10 Gesture Classes** — Palm, L, Fist, Fist Moved, Thumb, Index, OK, Palm Moved, C, Down
- **Real-time webcam recognition** with live confidence visualization
- **Two inference modes** — Image Classification or MediaPipe Landmark Classification
- **3 model backbones** — Custom CNN, MobileNetV2, EfficientNetB0
- **JWT Authentication** — Register, Login, Role-based access (admin/user)
- **Admin Panel** — Trigger model retraining, view training history, manage users
- **Prediction Analytics** — Gesture frequency charts, exportable CSV history
- **Production-ready** — Deployable to Vercel + Render + Neon PostgreSQL without Docker

---

## 🏗️ Architecture

```
┌─────────────────────────┐
│  React + TypeScript     │  ← Vercel
│  Vite + Tailwind CSS    │
└────────────┬────────────┘
             │ HTTPS (REST)
┌────────────▼────────────┐
│  FastAPI Backend        │  ← Render / Railway
│  JWT Auth + SlowAPI     │
│  Prometheus Metrics     │
└────────────┬────────────┘
             │
   ┌─────────┴──────────┐
   │                    │
┌──▼──────┐    ┌────────▼────────┐
│PostgreSQL│   │ TensorFlow Model│
│ Neon/    │   │ (CNN / MobileNet│
│ Supabase │   │  / EfficientNet)│
└──────────┘   └─────────────────┘
```

---

## 📁 Project Structure

```
Hand_Gestre_Rec/
├── ai/                         # AI pipeline
│   ├── download_dataset.py     # Kaggle dataset downloader
│   ├── augment.py              # Data augmentation
│   ├── train.py                # Training (CNN/MobileNetV2/EfficientNetB0)
│   ├── evaluate.py             # Model evaluation
│   └── inference.py            # GesturePredictor (image + landmark modes)
│
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── core/
│   │   ├── config.py           # Pydantic Settings
│   │   ├── security.py         # JWT + bcrypt
│   │   └── logging.py          # Structured logging
│   ├── db/database.py          # SQLAlchemy engine + session
│   ├── models/                 # ORM models (User, Prediction, TrainingJob, AuditLog)
│   ├── schemas/                # Pydantic schemas (auth, predict, training, admin)
│   └── routers/                # API routes (auth, predict, training, admin)
│
├── frontend/
│   └── src/
│       ├── api/client.ts       # Axios + auto-refresh interceptors
│       ├── hooks/              # useAuth, useWebcam, usePrediction
│       ├── components/         # Webcam, GestureOverlay, ConfidenceBar, ...
│       └── pages/              # Hero, Login, Register, Dashboard
│
├── alembic/                    # Database migrations
├── tests/                      # pytest test suite
├── docker/                     # Dockerfiles
├── .github/workflows/          # CI/CD GitHub Actions
├── docker-compose.yml
├── requirements.txt
└── context.md                  # Project tracking (read this first!)
```

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### 1. Clone and Configure

```bash
git clone https://github.com/your-username/hand-gesture-recognition.git
cd hand-gesture-recognition
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY
```

### 2. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend Setup

```bash
cd frontend
cp .env.example .env          # VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

App: http://localhost:5173

---

## 🧠 Training a Model

### Step 1 — Download Dataset

```bash
# Set Kaggle credentials in .env
# KAGGLE_USERNAME=your_username
# KAGGLE_KEY=your_api_key

python -m ai.download_dataset
```

### Step 2 — Augment Data

```bash
python -m ai.augment
```

### Step 3 — Train

```bash
# Custom CNN (fastest)
python -m ai.train --backbone cnn --epochs 50

# MobileNetV2 (better accuracy)
python -m ai.train --backbone mobilenetv2 --epochs 30

# EfficientNetB0 (best accuracy)
python -m ai.train --backbone efficientnetb0 --epochs 30
```

Model saved to `models/best_model.keras` and `models/class_names.json`.

### Step 4 — Evaluate

```bash
python -m ai.evaluate
```

---

## 🌐 Production Deployment (Vercel + Render + Neon)

### Database — Neon PostgreSQL

1. Create a free database at [neon.tech](https://neon.tech)
2. Copy the connection string → set `DATABASE_URL` in Render env vars

### Backend — Render

1. Connect your GitHub repo to [render.com](https://render.com)
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Set environment variables (copy from `.env.example`)
5. Run migrations: add a one-off job `alembic upgrade head`

### Frontend — Vercel

1. Import GitHub repo at [vercel.com](https://vercel.com)
2. **Framework**: Vite
3. **Root Directory**: `frontend`
4. **Environment Variable**: `VITE_API_URL=https://your-render-app.onrender.com`

---

## 🐳 Docker (Optional)

```bash
# Start everything (backend + frontend + postgres + pgadmin)
docker compose up -d

# Dev mode with pgAdmin
docker compose --profile dev up -d

# View logs
docker compose logs -f backend
```

---

## 🔑 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | — | Register new user |
| POST | `/api/v1/auth/login` | — | Login and get JWT tokens |
| POST | `/api/v1/auth/refresh` | — | Refresh access token |
| GET | `/api/v1/auth/me` | ✅ | Get current user |
| POST | `/api/v1/predict` | ✅ | Run gesture inference (base64) |
| GET | `/api/v1/predictions` | ✅ | Get prediction history |
| POST | `/api/v1/training/start` | 👑 Admin | Start training job |
| GET | `/api/v1/training/status/{id}` | ✅ | Poll training job |
| GET | `/api/v1/training/history` | ✅ | List training jobs |
| GET | `/api/v1/admin/stats` | 👑 Admin | Platform statistics |
| GET | `/api/v1/admin/users` | 👑 Admin | User list |
| DELETE | `/api/v1/admin/users/{id}` | 👑 Admin | Deactivate user |
| GET | `/health` | — | Health check |
| GET | `/metrics` | — | Prometheus metrics |

Interactive docs: `http://localhost:8000/docs`

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./gesture_recognition.db` | DB connection string |
| `SECRET_KEY` | — | JWT signing key (required in prod) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `INFERENCE_MODE` | `image` | `image` or `landmark` |
| `MODEL_BACKBONE` | `cnn` | `cnn`, `mobilenetv2`, or `efficientnetb0` |
| `MODEL_PATH` | `models/best_model.keras` | Path to trained model |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `VITE_API_URL` | `http://localhost:8000` | Frontend API base URL |
| `KAGGLE_USERNAME` | — | For dataset download |
| `KAGGLE_KEY` | — | For dataset download |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'feat: add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
