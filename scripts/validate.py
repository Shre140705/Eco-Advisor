from pathlib import Path
import csv
import json
from jsonschema import validate

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / 'data' / 'schemas'

for data_name, schema_name in [('foods.json', 'food.schema.json'), ('packaging.json', 'packaging.schema.json'), ('sources.json', 'source.schema.json')]:
    records = json.loads((ROOT / 'data' / data_name).read_text())
    schema = json.loads((SCHEMA_DIR / schema_name).read_text())
    for record in records:
        validate(record, schema)
    print(f'{data_name}: {len(records)} records validated against {schema_name}')

training_path = ROOT / 'data' / 'processed' / 'synthetic_training_dataset.csv'
if training_path.exists():
    schema = json.loads((SCHEMA_DIR / 'training-row.schema.json').read_text())
    with training_path.open(newline='') as f:
        row = next(csv.DictReader(f))
    numeric = ['temperature_c', 'relative_humidity', 'storage_duration_days', 'transport_duration_days', 'shelf_life_days']
    for key in numeric:
        if key in row:
            row[key] = float(row[key])
    row['source_ids'] = [x for x in row.get('source_ids', '').strip('[]').replace("'", '').split(',') if x]
    validate(row, schema)
    print('synthetic_training_dataset.csv: first generated row validated against training-row.schema.json')

routes = json.loads((ROOT / 'public' / 'manus-routes.json').read_text())
assert routes['routes'] and all(route['path'].startswith('/') for route in routes['routes'])
print(f"manus-routes.json: {len(routes['routes'])} routes validated")
