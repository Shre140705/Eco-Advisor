"""EcoAdvisor transparent decision engine.

Scores are comparative decision-support indicators. They are not certified LCA
outputs, regulatory approvals, or experimentally validated shelf-life measurements.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

_MODEL = None
_MODEL_INFO: dict[str, Any] | None = None


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, float(value))), 4)


def fit(requirement: float, performance: float) -> float:
    if requirement <= 0:
        return 100.0
    return clamp(100.0 * performance / requirement)


def _load_model() -> tuple[Any, dict[str, Any]]:
    global _MODEL, _MODEL_INFO
    if _MODEL is not None:
        return _MODEL, (_MODEL_INFO or {})
    model_path = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "random_forest.joblib"
    metadata_path = model_path.with_name("metadata.json")
    try:
        from joblib import load
        _MODEL = load(model_path)
        _MODEL_INFO = {"version": "rf-synthetic-v1"}
        if metadata_path.exists():
            import json
            _MODEL_INFO.update(json.loads(metadata_path.read_text(encoding="utf-8")))
        return _MODEL, _MODEL_INFO
    except Exception:
        _MODEL = False
        _MODEL_INFO = {"version": "heuristic-fallback-v1"}
        return None, _MODEL_INFO


def compatibility(food: dict[str, Any], package: dict[str, Any], conditions: dict[str, Any]) -> dict[str, Any]:
    p = package["properties"]
    barrier = {
        "oxygen": fit(food["required_oxygen_barrier"], p["oxygen_barrier"]),
        "moisture": fit(food["required_moisture_barrier"], p["moisture_barrier"]),
        "light": fit(food["required_light_barrier"], p["light_barrier"]),
        "mechanical": fit(food["mechanical_protection_required"], p["mechanical_strength"]),
    }
    if conditions.get("light_exposure") == "HIGH":
        barrier["light"] = fit(min(100, food["required_light_barrier"] + 15), p["light_barrier"])
    if conditions.get("transportation") == "LONG_DISTANCE":
        barrier["mechanical"] = min(barrier["mechanical"], fit(min(100, food["mechanical_protection_required"] + 15), p["mechanical_strength"]))
    compatibility_parts = [
        p["acidic_food_compatibility"] if (food.get("ph_value") or 7) < 5 else 80,
        p["high_moisture_compatibility"] if food["moisture_level"] >= 70 else 80,
        p["oily_food_compatibility"] if food["fat_content"] >= 25 else 80,
        p["liquid_food_compatibility"] if food["physical_state"] == "LIQUID" else 80,
    ]
    if conditions.get("mechanical_protection") is not None:
        barrier["mechanical"] = fit(float(conditions["mechanical_protection"]), p["mechanical_strength"])
    temperature = float(conditions["temperature_c"])
    heat_fit = 100.0 if temperature <= 35 else fit(100, p["heat_resistance"])
    barrier_fit = 0.35 * barrier["oxygen"] + 0.35 * barrier["moisture"] + 0.15 * barrier["light"] + 0.15 * barrier["mechanical"]
    food_fit = sum(compatibility_parts) / len(compatibility_parts)
    overall = 0.62 * barrier_fit + 0.28 * food_fit + 0.10 * heat_fit
    reasons: list[str] = []
    if food["physical_state"] == "LIQUID" and p["liquid_food_compatibility"] < 45: reasons.append("low liquid-food compatibility")
    if food["moisture_sensitivity"] >= 75 and p["moisture_barrier"] < 45: reasons.append("insufficient moisture barrier for a moisture-sensitive food")
    if food["oxygen_sensitivity"] >= 70 and p["oxygen_barrier"] < 50: reasons.append("insufficient oxygen barrier for an oxygen-sensitive food")
    if conditions.get("refrigeration_required") and temperature > 8: reasons.append("requested refrigerated food is above the default cold-storage threshold")
    eligible = overall >= 48 and not (food["physical_state"] == "LIQUID" and p["liquid_food_compatibility"] < 30)
    return {"score": clamp(overall), "eligible": eligible, "barrier_fit": {k: round(v, 1) for k, v in barrier.items()}, "food_fit": round(food_fit, 1), "reason": "; ".join(reasons) if reasons else None}


def predict_shelf_life(food: dict[str, Any], package: dict[str, Any], conditions: dict[str, Any], model_info: dict[str, Any] | None = None) -> dict[str, Any]:
    p = package["properties"]
    model, info = _load_model()
    if model is not None:
        try:
            import pandas as pd
            features = pd.DataFrame([{
                "food_category": food["food_category"], "physical_state": food["physical_state"], "packaging_category": package["packaging_category"],
                "temperature_c": float(conditions["temperature_c"]), "relative_humidity": float(conditions["relative_humidity"]), "perishability": food["perishability"],
                "moisture_sensitivity": food["moisture_sensitivity"], "oxygen_sensitivity": food["oxygen_sensitivity"], "oxygen_barrier": p["oxygen_barrier"],
                "moisture_barrier": p["moisture_barrier"], "mechanical_strength": p["mechanical_strength"], "sustainability": (p["recyclability"] + p["carbon_footprint_score"]) / 2,
            }])
            predicted = max(0.5, float(model.predict(features)[0]))
            return {"days": round(predicted, 2), "status": "SYNTHETIC_MODEL", "model_version": info.get("version", "rf-synthetic-v1"), "warning": "Model estimate trained on synthetic/curated rows; real-world validation requires experimentally measured shelf-life data."}
        except Exception:
            pass
    temperature = float(conditions["temperature_c"])
    humidity = float(conditions["relative_humidity"])
    requested = float(conditions["storage_duration_days"])
    barrier = compatibility(food, package, conditions)
    temp_delta = abs(temperature - float(food["default_temperature_c"]))
    temp_penalty = min(0.72, temp_delta * (0.012 + food["perishability"] / 10000))
    humidity_delta = abs(humidity - float(food["default_relative_humidity"]))
    humidity_penalty = min(0.38, humidity_delta / 240.0 * (0.4 + food["moisture_sensitivity"] / 150.0))
    transport_penalty = 0.12 if conditions.get("transportation") == "LONG_DISTANCE" else (0.05 if conditions.get("transportation") == "SHORT_DISTANCE" else 0)
    barrier_multiplier = 0.55 + barrier["score"] / 220.0
    preservation_multiplier = max(0.22, 1.0 - temp_penalty - humidity_penalty - transport_penalty) * barrier_multiplier
    base = max(1.0, float(food["typical_shelf_life_days"]))
    estimated = max(0.5, base * preservation_multiplier * (1.0 - min(0.25, conditions.get("transport_duration_days", 0) / 120.0)))
    estimated = min(estimated, max(base * 1.2, requested * 1.5))
    return {"days": round(estimated, 2), "status": "ASSUMPTION_HEURISTIC", "model_version": info.get("version", "heuristic-fallback-v1"), "warning": "Computational estimate; the current catalogue uses assumption-based profiles. Experimental validation is required for operational use."}


def sustainability(package: dict[str, Any]) -> float:
    p = package["properties"]
    value = (0.30 * ((p["recyclability"] + p["biodegradability"] + p["compostability"] + p["reusability"]) / 4) + 0.20 * p["carbon_footprint_score"] + 0.20 * p["recyclability"] + 0.10 * p["biodegradability"] + 0.10 * p["compostability"] + 0.10 * p["material_recovery_potential"])
    return clamp(value)


def circularity(package: dict[str, Any]) -> float:
    p = package["properties"]
    value = 0.20 * p["recycled_content"] + 0.20 * p["recyclability"] + 0.20 * p["reusability"] + 0.15 * p["material_recovery_potential"] + 0.15 * p["material_circularity"] + 0.10 * p["compostability"]
    return clamp(value)


def topsis(rows: list[dict[str, Any]], weights: dict[str, float]) -> list[dict[str, Any]]:
    criteria = ["shelf_life", "suitability", "oxygen_fit", "moisture_fit", "recyclability", "biodegradability", "circularity", "carbon", "cost"]
    directions = {"shelf_life": "benefit", "suitability": "benefit", "oxygen_fit": "benefit", "moisture_fit": "benefit", "recyclability": "benefit", "biodegradability": "benefit", "circularity": "benefit", "carbon": "benefit", "cost": "cost"}
    w = {c: float(weights.get(c, 1 / len(criteria))) for c in criteria}; total = sum(max(0.0, x) for x in w.values()) or 1.0; w = {c: max(0.0, w[c]) / total for c in criteria}
    denoms = {c: math.sqrt(sum((float(r[c]) or 0) ** 2 for r in rows)) or 1.0 for c in criteria}; weighted = [{c: (float(r[c]) / denoms[c]) * w[c] for c in criteria} for r in rows]
    ideal = {c: (max(v[c] for v in weighted) if directions[c] == "benefit" else min(v[c] for v in weighted)) for c in criteria}; nadir = {c: (min(v[c] for v in weighted) if directions[c] == "benefit" else max(v[c] for v in weighted)) for c in criteria}
    result = []
    for r, v in zip(rows, weighted):
        dp = math.sqrt(sum((v[c] - ideal[c]) ** 2 for c in criteria)); dn = math.sqrt(sum((v[c] - nadir[c]) ** 2 for c in criteria)); score = dn / (dp + dn) if dp + dn else 0.5
        item = dict(r); item["topsis_score"] = round(score, 5); item["topsis_weights"] = {k: round(vv, 4) for k, vv in w.items()}; result.append(item)
    return sorted(result, key=lambda x: (-x["topsis_score"], x["packaging_name"]))


def final_score(row: dict[str, Any], priorities: dict[str, float]) -> float:
    shelf = clamp(row["shelf_life"] / max(row["baseline_shelf_life"], 1) * 100); p = {"preservation": priorities.get("preservation", 0.25), "sustainability": priorities.get("sustainability", 0.20), "circularity": priorities.get("circularity", 0.15), "cost": priorities.get("cost", 0.10), "end_of_life": priorities.get("end_of_life", 0.10)}; fixed = 0.20; total = sum(p.values()) + fixed; p = {k: v / total for k, v in p.items()}
    return round(clamp(fixed * row["suitability"] + p["preservation"] * shelf + p["sustainability"] * row["sustainability"] + p["circularity"] * row["circularity"] + p["cost"] * row["cost"] + p["end_of_life"] * row["end_of_life"]), 4)


def explain(row: dict[str, Any], food: dict[str, Any]) -> dict[str, Any]:
    strengths = [label for key, label in [("oxygen_fit", "oxygen protection"), ("moisture_fit", "moisture management"), ("suitability", "food-package compatibility"), ("circularity", "circularity profile")] if row.get(key, 0) >= 70][:3] or ["the best overall balance among eligible alternatives"]
    limitations = []
    if row["carbon"] < 50: limitations.append("the comparative carbon indicator is less favourable than some alternatives")
    if row["cost"] < 45: limitations.append("relative cost is higher than lower-cost options")
    if row["circularity"] < 45: limitations.append("the circularity score is limited by the available end-of-life pathway")
    if not limitations: limitations.append("material performance depends on format, thickness, coating, and local infrastructure")
    return {"why": f"{row['packaging_name']} is recommended for {food['food_name']} because it provides {', '.join(strengths)} while balancing predicted shelf life, sustainability, circularity, and cost.", "advantages": strengths, "limitations": limitations, "end_of_life": row.get("disposal_method", "Verify local recycling or composting guidance."), "alternative_note": "Alternatives remain visible so the user can compare trade-offs; this is not a universal material ranking."}
