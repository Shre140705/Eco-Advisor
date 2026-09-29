from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ARTIFACTS = ROOT / "ml" / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def make_training_data(seed: int = 42, rows_per_pair: int = 6) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    foods = json.loads((DATA / "foods.json").read_text())
    packages = json.loads((DATA / "packaging.json").read_text())
    records = []
    row_id = 1
    for food in foods:
        for package in packages:
            p = package["properties"]
            for _ in range(rows_per_pair):
                temperature = float(food["default_temperature_c"]) + rng.normal(0, 5)
                humidity = np.clip(float(food["default_relative_humidity"]) + rng.normal(0, 10), 0, 100)
                barrier = (p["oxygen_barrier"] + p["moisture_barrier"] + p["mechanical_strength"]) / 3
                temp_penalty = abs(temperature - float(food["default_temperature_c"])) * 0.10
                humidity_penalty = abs(humidity - float(food["default_relative_humidity"])) * 0.04
                shelf = float(food["typical_shelf_life_days"]) * (0.45 + barrier / 180) - temp_penalty - humidity_penalty + rng.normal(0, 0.4)
                records.append({"row_id": f"ROW-{row_id:06d}", "food_id": food["food_id"], "packaging_id": package["packaging_id"], "food_category": food["food_category"], "physical_state": food["physical_state"], "packaging_category": package["packaging_category"], "temperature_c": round(temperature, 3), "relative_humidity": round(humidity, 3), "storage_duration_days": float(food["typical_shelf_life_days"]), "transport_duration_days": 1.0, "perishability": food["perishability"], "moisture_sensitivity": food["moisture_sensitivity"], "oxygen_sensitivity": food["oxygen_sensitivity"], "oxygen_barrier": p["oxygen_barrier"], "moisture_barrier": p["moisture_barrier"], "mechanical_strength": p["mechanical_strength"], "sustainability": (p["recyclability"] + p["carbon_footprint_score"]) / 2, "shelf_life_days": max(0.5, round(shelf, 3)), "data_status": "SYNTHETIC", "source_ids": ["SRC-014"], "generator_version": "synthetic-v1", "notes": "Generated for computational workflow demonstration; not an experimental observation."})
                row_id += 1
    return pd.DataFrame(records)


def train() -> dict:
    df = make_training_data()
    out_csv = DATA / "processed" / "synthetic_training_dataset.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    target = "shelf_life_days"
    features = [c for c in df.columns if c not in {target, "row_id", "food_id", "packaging_id", "storage_duration_days", "transport_duration_days", "data_status", "source_ids", "generator_version", "notes"}]
    categorical = ["food_category", "physical_state", "packaging_category"]
    numeric = [x for x in features if x not in categorical]
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), categorical), ("num", "passthrough", numeric)])
    model = Pipeline([("preprocess", pre), ("model", RandomForestRegressor(n_estimators=220, random_state=42, min_samples_leaf=2, n_jobs=-1))])
    x_train, x_test, y_train, y_test = train_test_split(df[features], df[target], test_size=0.2, random_state=42)
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    metrics = {"mae": round(float(mean_absolute_error(y_test, pred)), 4), "rmse": round(float(np.sqrt(mean_squared_error(y_test, pred))), 4), "r2": round(float(r2_score(y_test, pred)), 4), "rows": int(len(df)), "data_status": "SYNTHETIC", "warning": "Metrics describe performance on generated data and do not establish real-world accuracy."}
    dump(model, ARTIFACTS / "random_forest.joblib")
    (ARTIFACTS / "metadata.json").write_text(json.dumps({"version": "rf-synthetic-v1", "features": features, "metrics": metrics}, indent=2))
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
