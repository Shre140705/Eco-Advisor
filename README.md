# EcoAdvisor

EcoAdvisor is a full-stack decision-support system for sustainable food-packaging selection based on food preservation, shelf-life estimation, circularity, environmental indicators, and cost.

> This educational application provides a comparative computational assessment. It is not a certified life-cycle assessment, food-contact approval, or experimentally validated shelf-life instrument.

## Included

- React + Vite + TypeScript dashboard
- FastAPI REST API with Pydantic validation
- SQLite fallback for immediate local execution
- MySQL-compatible schema and Docker Compose setup
- 18 provenance-labelled food profiles and 12 packaging profiles
- Random Forest synthetic-data training pipeline
- Compatibility gate before ranking
- TOPSIS multi-criteria ranking
- EcoAdvisor Sustainability Score and Circularity Score
- Explainable recommendation with alternatives and end-of-life notes
- Comparison charts, sensitivity scenarios, history, methodology, and references
- Tests for API, validation, engine, and deterministic ranking

## Quick start

```bash
# backend dependencies
python3 -m pip install -r backend/requirements.txt

# frontend dependencies and build
cd frontend
npm install
npm run build
cd ..

# optional synthetic model training
python3 ml/train_model.py

# start one same-origin app
PORT=3000 uvicorn backend.app:app --host 0.0.0.0 --port 3000
```

Open `http://localhost:3000`. The API is under `/api`. The application uses `ecoadvisor.db` for history by default.

## Cloud Deployment & Hosting

### Option 1: Render (Recommended - Free Tier)
1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com) using your GitHub account.
3. Click **New +** -> **Web Service** (or use Blueprints with the included `render.yaml`).
4. Connect your `ecoadvisor` repository.
5. Render detects the multi-stage `Dockerfile` automatically and builds both the React UI and FastAPI backend.
6. Click **Deploy Web Service** to get a live URL (e.g. `https://ecoadvisor.onrender.com`).

### Option 2: Railway or Koyeb
1. Connect your GitHub repository to [Railway](https://railway.app) or [Koyeb](https://koyeb.com).
2. It detects the `Dockerfile` and deploys both frontend and backend on port 3000.

## MySQL mode

Use the included `docker-compose.yml`:

```bash
docker compose up --build
```

The schema is in `database/schema.sql`. The current demo persists history through SQLite for zero-setup portability; `DATABASE_URL` and the MySQL schema are included for the full deployment extension.

## API endpoints

- `GET /api/health`
- `GET /api/foods`
- `GET /api/packaging`
- `GET /api/sources`
- `POST /api/predict-shelf-life`
- `POST /api/rank-packaging`
- `POST /api/recommend`
- `GET /api/recommendation/{id}`
- `GET /api/recommendations/history`
- `POST /api/sensitivity-analysis`

## Model workflow

`ml/train_model.py` creates `data/processed/synthetic_training_dataset.csv`, trains a Random Forest Regressor, and saves `ml/artifacts/random_forest.joblib` plus evaluation metadata. Every row is labelled `SYNTHETIC`. The metrics show computational workflow performance on generated data and do not establish real-world accuracy.

## Scoring notes

- Compatibility is checked before ranking; severe food-package mismatches are excluded.
- TOPSIS uses benefit and cost criteria with configurable priorities.
- Sustainability is a transparent 0–100 comparative indicator, not an LCA.
- Circularity combines recycled content, recyclability, reusability, recovery, end-of-life, and compostability.
- The final recommendation balances preservation, shelf life, sustainability, circularity, cost, and end-of-life.

## Tests

```bash
python3 scripts/validate.py
python3 -m pytest -q
```

## Limitations and future data work

The catalogue contains assumptions and family-level profiles. Packaging performance varies with grade, thickness, coating, format, closure, food formulation, and local infrastructure. Real deployment needs food-specific measured shelf-life data, product-specific barrier measurements with test conditions, food-contact/regulatory review, local recycling data, and a full LCA with defined functional unit and system boundary.
