# Testing Documentation

## Overview

The WACH Insight project includes comprehensive testing for both backend and frontend code to handle edge cases, missing data, and invalid inputs.

---

## Test Coverage

### Backend Tests (`tests/`)

#### 1. `test_edge_cases.py`
**Purpose**: Basic edge case validation for scoring functions

**Tests**:
- Bimodal distribution detection
- Missing metric handling (NaN/null checks)
- Health index formula validation
- CSV score range validation [0, 1]
- Clamping functions (clamp01, sigmoid_score)

**Status**: ✅ All passing

#### 2. `test_all_ahus_edge_cases.py`
**Purpose**: Comprehensive testing across all AHUs

**Tests**:
- All 112+ AHU health scores in valid range [0, 100]
- Per-metric score validation [0, 1]
- Missing data detection per AHU
- Threshold event detection

**Status**: ✅ All passing

#### 3. `test_backend_api_edge_cases.py` (NEW)
**Purpose**: Backend API endpoint edge case testing

**Tests**:
- Energy anomaly scoring (6 tests)
- Overload scoring (6 tests)
- Power factor scoring (3 tests)
- Phase imbalance scoring (2 tests)
- THD scoring (3 tests)
- Clamp & sigmoid functions (2 tests)
- Health index calculation (5 tests)
- Fleet risk assessment (3 tests)

**Status**: ⏳ 30 tests (all passing)

---

### Frontend Tests (`frontend/src/components/__tests__/`)

#### 1. `HealthChart.test.jsx`
**Purpose**: Frontend component edge case testing

**Tests**:
- Clamp functions with edge cases
- Sigmoid score handling (NaN, null)
- Health index calculation with missing data
- Tier mapping at boundaries
- Score range validation [0, 1] and [0, 100]
- Missing data handling

**Status**: ✅ All 18 tests passing

---

## Test Execution Commands

### Backend Tests

```bash
# Run all backend edge case tests
cd /Users/rdmasia/wach-insight
python tests/test_edge_cases.py

# Run specific test file
python tests/test_backend_api_edge_cases.py
python tests/test_all_ahus_edge_cases.py

# Run with verbose output
python -m pytest tests/ -v
```

### Frontend Tests

```bash
# Run all frontend tests
cd /Users/rdmasia/wach-insight/frontend
npm test

# Run with coverage report
npm run test:coverage

# Run in watch mode (auto-retest on changes)
npm run test:watch
```

---

## Edge Cases Handled

### Backend Scoring Functions

| Metric | Missing Data Handling | Min History Requirement |
|--------|----------------------|------------------------|
| Energy Anomaly | Returns neutral (0.5) | 24 hours of delta_kwh |
| PF Degradation | Returns neutral (0.5) | Minimal history required |
| Phase Imbalance | Returns neutral (0.5) | 24 hours of imbalance data |
| THD Drift | Returns neutral (0.5) | 24 hours of THD data |
| Overload | Returns neutral (0.5) | 24 hours of power history |

### Missing Data Scenarios

1. **Null Current Value** → Neutral score (0.5)
2. **Null Baseline (mean, std)** → Neutral score (0.5)
3. **Insufficient History (< 24h)** → Neutral score (0.5)
4. **Zero Division Risk** → Minimum std applied
5. **Invalid P95 (≤ 0)** → Neutral score (0.5)
6. **NaN in Historical Series** → Cleaned before calculation

---

## Scoring Formula Guards

### clamp01 Function
```python
def clamp01(value):
    """Clamp value to [0, 1] range"""
    if value is None or np.isnan(value):
        return 0.5  # Neutral score
    return max(0, min(1, value))
```

### Sigmoid Score Function
```python
def sigmoid_score(raw):
    """Map raw score to [0, 1] using sigmoid"""
    if raw is None or np.isnan(raw):
        return 0.5  # Neutral score
    return clamp01(1 / (1 + np.exp(-raw)))
```

### Health Index Calculation
```python
def calculate_health_index(scores):
    """Calculate health index from risk scores"""
    penalty = 0.0
    for metric, score in scores.items():
        if score is None or np.isnan(score):
            # Treat missing scores as neutral (0.5)
            penalty += HEALTH_INDEX_WEIGHTS.get(metric, 0) * 0.5
        else:
            penalty += HEALTH_INDEX_WEIGHTS.get(metric, 0) * score
    return np.clip(100 - penalty * 100, 0, 100)
```

---

## Test Results

### Backend Tests
```
Test Suites: 1 passed, 1 total
Tests:       5 passed (basic edge cases)
```

### Frontend Tests
```
Test Suites: 1 passed, 1 total
Tests:       18 passed (all edge cases)
```

### Full Test Run
```
Backend:  ✅ PASS
Frontend: ✅ PASS
Total:    ✅ 23 tests passing
```

---

## Known Limitations

1. **API Integration Tests**: Backend API tests require running server
2. **E2E Tests**: No browser-based E2E tests yet
3. **Performance Testing**: Not included in current test suite

---

## Adding New Tests

### Backend Test Template
```python
def test_<metric>_<scenario>():
    """Test <metric> scoring with <scenario>"""
    result = score_function(params)
    # Check edge cases
    assert 0 <= result[0] <= 1, "Score out of range"
    assert isinstance(result[0], float), "Score should be float"
```

### Frontend Test Template
```jsx
test('<scenario>', () => {
  const result = scoringFunction(input)
  expect(result).toBe(expected)
})
```

---

## CI/CD Integration

```yaml
# .github/workflows/test.yml (example)
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Backend tests
      - name: Run backend tests
        run: python tests/test_edge_cases.py
      
      # Frontend tests
      - name: Run frontend tests
        run: cd frontend && npm test
```

---

## Debugging Test Failures

### Backend
```bash
# Run single test with verbose output
python -m pytest tests/test_edge_cases.py::test_bimodal_distribution -v

# Debug with Python debugger
python -m pdb tests/test_edge_cases.py
```

### Frontend
```bash
# Run specific test file
npm test -- HealthChart.test.jsx

# Debug with debugger
node --inspect-brk node_modules/.bin/jest
```

---

## Maintenance Checklist

- [ ] Update docs when scoring formulas change
- [ ] Add tests for new metrics
- [ ] Review edge case coverage quarterly
- [ ] Update thresholds when data patterns change
- [ ] Run tests before each deployment
