from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / "engine"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engine.decision_engine import circularity, compatibility, explain, final_score, predict_shelf_life, sustainability, topsis


def load_json(name: str) -> list[dict[str, Any]]:
    with (ROOT / "data" / name).open(encoding="utf-8") as f:
        return json.load(f)


FOODS = load_json("foods.json")
PACKAGING = load_json("packaging.json")
SOURCES = load_json("sources.json")
DB_PATH = Path(os.getenv("ECOADVISOR_DB", str(ROOT / "ecoadvisor.db")))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ecoadvisor.db")
MYSQL_ENGINE = None


def init_db() -> None:
    global MYSQL_ENGINE
    if DATABASE_URL.startswith("mysql"):
        from sqlalchemy import create_engine, text
        for attempt in range(12):
            try:
                MYSQL_ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
                with MYSQL_ENGINE.begin() as con:
                    con.execute(text("CREATE TABLE IF NOT EXISTS recommendations (recommendation_id BIGINT PRIMARY KEY AUTO_INCREMENT, food_id VARCHAR(20) NOT NULL, request_json JSON NOT NULL, result_json JSON NOT NULL, created_at VARCHAR(64) NOT NULL)"))
                return
            except Exception:
                MYSQL_ENGINE = None
                if attempt < 11:
                    time.sleep(2)
    with sqlite3.connect(DB_PATH) as con:
        con.execute("CREATE TABLE IF NOT EXISTS recommendations (recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT, food_id TEXT NOT NULL, request_json TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL)")
        con.commit()


def insert_recommendation(food_id: str, request_json: str, result_json: str, created_at: str) -> int:
    if MYSQL_ENGINE is not None:
        from sqlalchemy import text
        with MYSQL_ENGINE.begin() as con:
            con.execute(text("INSERT INTO recommendations(food_id, request_json, result_json, created_at) VALUES (:food_id, :request_json, :result_json, :created_at)"), {"food_id": food_id, "request_json": request_json, "result_json": result_json, "created_at": created_at})
            return int(con.execute(text("SELECT LAST_INSERT_ID()" )).scalar())
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("INSERT INTO recommendations(food_id, request_json, result_json, created_at) VALUES (?, ?, ?, ?)", (food_id, request_json, result_json, created_at)); con.commit(); return int(cur.lastrowid)


def fetch_recommendation(recommendation_id: int):
    if MYSQL_ENGINE is not None:
        from sqlalchemy import text
        with MYSQL_ENGINE.connect() as con:
            return con.execute(text("SELECT result_json FROM recommendations WHERE recommendation_id = :id"), {"id": recommendation_id}).fetchone()
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("SELECT result_json FROM recommendations WHERE recommendation_id = ?", (recommendation_id,)).fetchone()


def fetch_history(limit: int):
    if MYSQL_ENGINE is not None:
        from sqlalchemy import text
        with MYSQL_ENGINE.connect() as con:
            return con.execute(text("SELECT recommendation_id, food_id, result_json, created_at FROM recommendations ORDER BY recommendation_id DESC LIMIT :limit"), {"limit": limit}).fetchall()
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("SELECT recommendation_id, food_id, result_json, created_at FROM recommendations ORDER BY recommendation_id DESC LIMIT ?", (limit,)).fetchall()


init_db()


class Conditions(BaseModel):
    temperature_c: float = Field(default=4, ge=-30, le=60)
    relative_humidity: float = Field(default=60, ge=0, le=100)
    storage_duration_days: float = Field(default=7, gt=0, le=3650)
    transport_duration_days: float = Field(default=1, ge=0, le=365)
    transportation: Literal["LOCAL", "SHORT_DISTANCE", "LONG_DISTANCE"] = "LOCAL"
    refrigeration_required: bool = False
    light_exposure: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    mechanical_protection: float | None = Field(default=None, ge=0, le=100)


class Priorities(BaseModel):
    preservation: float = Field(default=0.25, ge=0, le=1)
    sustainability: float = Field(default=0.25, ge=0, le=1)
    circularity: float = Field(default=0.15, ge=0, le=1)
    cost: float = Field(default=0.10, ge=0, le=1)
    end_of_life: float = Field(default=0.10, ge=0, le=1)

    @field_validator("end_of_life")
    @classmethod
    def weights_are_possible(cls, value: float) -> float:
        return value


class RecommendationRequest(BaseModel):
    food_id: str = Field(min_length=1)
    conditions: Conditions = Conditions()
    priorities: Priorities = Priorities()


class PredictionRequest(BaseModel):
    food_id: str = Field(min_length=1)
    packaging_id: str = Field(min_length=1)
    conditions: Conditions = Conditions()


class RankingRequest(BaseModel):
    food_id: str = Field(min_length=1)
    conditions: Conditions = Conditions()
    priorities: Priorities = Priorities()


app = FastAPI(title="EcoAdvisor API", version="1.0.0", description="Transparent sustainable food-packaging decision support.")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def find_food(food_id: str) -> dict[str, Any]:
    item = next((x for x in FOODS if x["food_id"] == food_id), None)
    if not item:
        raise HTTPException(status_code=404, detail=f"Unknown food: {food_id}")
    return item


def find_package(packaging_id: str) -> dict[str, Any]:
    item = next((x for x in PACKAGING if x["packaging_id"] == packaging_id), None)
    if not item:
        raise HTTPException(status_code=404, detail=f"Unknown packaging: {packaging_id}")
    return item


def conditions_dict(c: Conditions) -> dict[str, Any]:
    data = c.model_dump()
    data["refrigeration_required"] = bool(c.refrigeration_required)
    return data


def build_rows(food: dict[str, Any], c: Conditions, priorities: Priorities) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cd = conditions_dict(c)
    eligible, excluded = [], []
    for package in PACKAGING:
        comp = compatibility(food, package, cd)
        prediction = predict_shelf_life(food, package, cd)
        p = package["properties"]
        row = {
            "packaging_id": package["packaging_id"], "packaging_name": package["material_name"], "packaging_category": package["packaging_category"],
            "shelf_life": prediction["days"], "baseline_shelf_life": max(float(food["typical_shelf_life_days"]), 1),
            "suitability": comp["score"], "oxygen_fit": comp["barrier_fit"]["oxygen"], "moisture_fit": comp["barrier_fit"]["moisture"],
            "light_fit": comp["barrier_fit"]["light"], "mechanical_fit": comp["barrier_fit"]["mechanical"], "food_fit": comp["food_fit"],
            "recyclability": p["recyclability"], "biodegradability": p["biodegradability"], "circularity": circularity(package),
            "sustainability": sustainability(package), "carbon": p["carbon_footprint_score"], "cost": 100 - p["relative_cost"],
            "end_of_life": round((p["recyclability"] + p["material_recovery_potential"] + p["compostability"]) / 3, 2),
            "relative_cost": p["relative_cost"], "reusability": p["reusability"], "compostability": p["compostability"],
            "recycled_content": p["recycled_content"], "disposal_method": package["disposal_method"], "recycling_method": package["recycling_method"],
            "data_status": package["data_status"], "confidence_level": p["confidence_level"], "eligible": comp["eligible"], "eligibility_reason": comp["reason"],
            "prediction": prediction,
        }
        (eligible if comp["eligible"] else excluded).append(row)
    if not eligible:
        raise HTTPException(status_code=422, detail={"message": "No suitable packaging alternatives meet the current compatibility threshold.", "excluded": excluded})
    return eligible, excluded


def make_result(request: RecommendationRequest) -> dict[str, Any]:
    food = find_food(request.food_id)
    rows, excluded = build_rows(food, request.conditions, request.priorities)
    w = request.priorities.model_dump()
    topsis_weights = {"shelf_life": w["preservation"], "suitability": 0.20, "oxygen_fit": 0.05, "moisture_fit": 0.05, "recyclability": w["sustainability"] * 0.4, "biodegradability": w["sustainability"] * 0.2, "circularity": w["circularity"], "carbon": w["sustainability"] * 0.4, "cost": w["cost"]}
    ranked = topsis(rows, topsis_weights)
    for row in ranked:
        row["final_score"] = final_score(row, w)
    ranked = sorted(ranked, key=lambda x: (-x["final_score"], -x["topsis_score"], x["packaging_name"]))
    for idx, row in enumerate(ranked, 1):
        row["rank"] = idx
        row["recommendation_explanation"] = explain(row, food) if idx == 1 else None
    top = ranked[0]
    return {
        "food": food, "conditions": request.conditions.model_dump(), "priorities": w, "recommended": top,
        "rankings": ranked, "excluded": excluded, "methodology": {"topsis": "TOPSIS with benefit/cost criteria and configurable preferences", "sustainability": "Transparent comparative 0–100 indicator; not a certified LCA", "circularity": "Recycled content, recyclability, reusability, recovery, end-of-life and compostability composite"},
        "limitations": ["Initial food/material profiles are curated assumptions and not universal material specifications.", "Shelf-life predictions are computational estimates; experimental validation is required.", "End-of-life performance depends on local infrastructure and the complete packaging format."]
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "ecoadvisor-api", "version": "1.0.0", "foods": len(FOODS), "packaging": len(PACKAGING), "database": "mysql" if MYSQL_ENGINE is not None else str(DB_PATH), "model": "rf-synthetic-v1" if (ROOT / "ml/artifacts/random_forest.joblib").exists() else "heuristic-fallback-v1"}


@app.get("/api/foods")
def foods() -> list[dict[str, Any]]:
    return FOODS


@app.get("/api/foods/{food_id}")
def food_detail(food_id: str) -> dict[str, Any]:
    return find_food(food_id)


@app.get("/api/packaging")
def packaging() -> list[dict[str, Any]]:
    return PACKAGING


@app.get("/api/packaging/{packaging_id}")
def packaging_detail(packaging_id: str) -> dict[str, Any]:
    return find_package(packaging_id)


@app.get("/api/sources")
def sources() -> list[dict[str, Any]]:
    return SOURCES


@app.post("/api/predict-shelf-life")
def predict(request: PredictionRequest) -> dict[str, Any]:
    food, package = find_food(request.food_id), find_package(request.packaging_id)
    return {"food": food["food_name"], "packaging": package["material_name"], "prediction": predict_shelf_life(food, package, conditions_dict(request.conditions))}


@app.post("/api/rank-packaging")
def rank(request: RankingRequest) -> dict[str, Any]:
    result = make_result(RecommendationRequest(food_id=request.food_id, conditions=request.conditions, priorities=request.priorities))
    return {"food": result["food"], "rankings": result["rankings"], "excluded": result["excluded"], "priorities": result["priorities"]}


@app.post("/api/recommend")
def recommend(request: RecommendationRequest) -> dict[str, Any]:
    result = make_result(request)
    created = datetime.now(timezone.utc).isoformat()
    result["recommendation_id"] = insert_recommendation(request.food_id, request.model_dump_json(), json.dumps(result), created)
    return result


@app.get("/api/recommendation/{recommendation_id}")
def recommendation(recommendation_id: int) -> dict[str, Any]:
    row = fetch_recommendation(recommendation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    result = json.loads(row[0]); result["recommendation_id"] = recommendation_id
    return result


@app.get("/api/recommendations/history")
def history(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    rows = fetch_history(limit)
    return [{"recommendation_id": r[0], "food_id": r[1], "food_name": json.loads(r[2])["food"]["food_name"], "recommended_packaging": json.loads(r[2])["recommended"]["packaging_name"], "final_score": json.loads(r[2])["recommended"]["final_score"], "created_at": r[3]} for r in rows]


@app.post("/api/sensitivity-analysis")
def sensitivity(request: RecommendationRequest) -> dict[str, Any]:
    scenarios = {
        "Balanced default": request.priorities.model_dump(),
        "Preservation-first": {"preservation": .45, "sustainability": .15, "circularity": .10, "cost": .10, "end_of_life": .10},
        "Sustainability-first": {"preservation": .20, "sustainability": .45, "circularity": .20, "cost": .05, "end_of_life": .10},
        "Cost-first": {"preservation": .20, "sustainability": .15, "circularity": .10, "cost": .40, "end_of_life": .15},
    }
    outputs = []
    for name, weights in scenarios.items():
        req = RecommendationRequest(food_id=request.food_id, conditions=request.conditions, priorities=Priorities(**weights))
        result = make_result(req)
        outputs.append({"scenario": name, "packaging": result["recommended"]["packaging_name"], "final_score": result["recommended"]["final_score"], "sustainability": result["recommended"]["sustainability"], "shelf_life": result["recommended"]["shelf_life"]})
    return {"food": find_food(request.food_id), "scenarios": outputs}


# Serve the built React application when it exists. API routes are declared before this mount.
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/manus-routes.json", include_in_schema=False)
def route_manifest() -> FileResponse:
    return FileResponse(ROOT / "public" / "manus-routes.json", media_type="application/json")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str) -> FileResponse:
    if DIST.exists() and (DIST / full_path).is_file():
        return FileResponse(DIST / full_path)
    if DIST.exists() and (DIST / "index.html").exists():
        return FileResponse(DIST / "index.html")
    return FileResponse(ROOT / "frontend" / "index.html")
