import json
from pathlib import Path
from engine.decision_engine import circularity, compatibility, sustainability, topsis

ROOT = Path(__file__).resolve().parents[1]
FOOD = json.loads((ROOT / 'data/foods.json').read_text())[2]
PACKAGE = json.loads((ROOT / 'data/packaging.json').read_text())[0]
CONDITIONS = {'temperature_c': 12, 'relative_humidity': 70, 'storage_duration_days': 7, 'transport_duration_days': 1, 'refrigeration_required': False}

def test_scores_are_bounded():
    assert 0 <= sustainability(PACKAGE) <= 100
    assert 0 <= circularity(PACKAGE) <= 100
    result = compatibility(FOOD, PACKAGE, CONDITIONS)
    assert 0 <= result['score'] <= 100

def test_topsis_returns_deterministic_order():
    rows = [
        {'packaging_name': 'A', 'shelf_life': 80, 'suitability': 80, 'oxygen_fit': 80, 'moisture_fit': 80, 'recyclability': 40, 'biodegradability': 30, 'circularity': 35, 'carbon': 30, 'cost': 80},
        {'packaging_name': 'B', 'shelf_life': 60, 'suitability': 60, 'oxygen_fit': 60, 'moisture_fit': 60, 'recyclability': 80, 'biodegradability': 80, 'circularity': 85, 'carbon': 80, 'cost': 40},
    ]
    weights = {k: 1 for k in ['shelf_life','suitability','oxygen_fit','moisture_fit','recyclability','biodegradability','circularity','carbon','cost']}
    ranked = topsis(rows, weights)
    assert len(ranked) == 2
    assert all(0 <= r['topsis_score'] <= 1 for r in ranked)
    assert [r['packaging_name'] for r in topsis(rows, weights)] == [r['packaging_name'] for r in topsis(rows, weights)]
