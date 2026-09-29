# EcoAdvisor API

All endpoints return JSON. The frontend uses same-origin relative requests under `/api`.

## Recommendation request

```json
{
  "food_id": "FOOD-003",
  "conditions": {
    "temperature_c": 12,
    "relative_humidity": 70,
    "storage_duration_days": 7,
    "transport_duration_days": 1,
    "transportation": "LOCAL",
    "refrigeration_required": false,
    "light_exposure": "MEDIUM",
    "mechanical_protection": 60
  },
  "priorities": {
    "preservation": 0.25,
    "sustainability": 0.25,
    "circularity": 0.15,
    "cost": 0.10,
    "end_of_life": 0.10
  }
}
```

`POST /api/recommend` returns the selected food, conditions, normalized priorities, recommended package, rankings, excluded alternatives, methodology notes, and limitations. `POST /api/sensitivity-analysis` returns preservation-first, sustainability-first, cost-first, and balanced scenarios.
