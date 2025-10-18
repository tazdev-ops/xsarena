---
# Rubric (Strict JSON)

Return JSON only:
```json
{
  "rubric_for": "string",
  "criteria": [{"name":"string","levels":[{"label":"Excellent","descriptor":"..."},{"label":"Good","descriptor":"..."},{"label":"Needs Work","descriptor":"..."}]}],
  "weights": {"CriterionName": 0.0}
}
```

Rules
- levels = 3–4
- Weights sum ≈ 1.0
