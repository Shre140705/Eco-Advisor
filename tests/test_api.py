from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_health_and_catalogues():
    assert client.get('/api/health').status_code == 200
    assert len(client.get('/api/foods').json()) >= 15
    assert len(client.get('/api/packaging').json()) >= 10

def test_recommendation_and_history():
    response = client.post('/api/recommend', json={'food_id':'FOOD-003','conditions':{'temperature_c':12,'relative_humidity':70,'storage_duration_days':7},'priorities':{}})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['recommended']['packaging_name']
    assert body['recommended']['rank'] == 1
    assert 0 <= body['recommended']['sustainability'] <= 100
    assert client.get('/api/recommendations/history').status_code == 200

def test_validation_and_unknown_food():
    assert client.post('/api/recommend', json={'food_id':'UNKNOWN'}).status_code == 404
    assert client.post('/api/recommend', json={'food_id':'FOOD-003','conditions':{'temperature_c':100}}).status_code == 422

def test_route_manifest_is_json():
    response = client.get('/manus-routes.json')
    assert response.status_code == 200
    assert 'routes' in response.json()

def test_model_artifact_and_scenario_controls_are_live():
    payload = {'food_id':'FOOD-003','conditions':{'temperature_c':12,'relative_humidity':70,'storage_duration_days':7,'transportation':'LOCAL','light_exposure':'MEDIUM'},'priorities':{}}
    first = client.post('/api/recommend', json=payload).json()
    assert first['recommended']['prediction']['status'] in {'SYNTHETIC_MODEL', 'ASSUMPTION_HEURISTIC'}
    changed = dict(payload)
    changed['conditions'] = {**payload['conditions'], 'transportation':'LONG_DISTANCE', 'light_exposure':'HIGH'}
    second = client.post('/api/recommend', json=changed).json()
    assert first['recommended']['shelf_life'] != second['recommended']['shelf_life'] or first['recommended']['suitability'] != second['recommended']['suitability']

def test_declared_routes_are_directly_served():
    for path in ['/comparison', '/sensitivity', '/history', '/methodology', '/references']:
        assert client.get(path).status_code == 200
