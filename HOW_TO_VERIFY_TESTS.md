# How to Verify the System Has Been Tested

This guide shows you multiple ways to verify that the automated denial handling system has been tested and is working correctly.

## Quick Verification

### 1. Run the Verification Script

```bash
python3 verify_tests.py
```

This script will:
- ✅ Check that all test files exist
- ✅ Verify code structure is correct
- ✅ Validate Python syntax
- ✅ Check test configuration
- ✅ Attempt to run pytest if available
- ✅ Show test coverage summary

### 2. Check Test Files Manually

All test files should exist:
```bash
ls -la tests/unit/
ls -la tests/integration/
```

Expected files:
- `tests/unit/test_state_machine.py`
- `tests/unit/test_validator.py`
- `tests/unit/test_classifier.py`
- `tests/unit/test_denial_agent.py`
- `tests/integration/test_api_routes.py`
- `tests/integration/test_celery_tasks.py`
- `tests/integration/test_denial_workflow.py`

## Full Test Execution

### Option 1: Using pytest (Recommended)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run all tests:**
   ```bash
   pytest tests/ -v
   ```

3. **Run with coverage:**
   ```bash
   pytest --cov=. --cov-report=html --cov-report=term-missing
   open htmlcov/index.html  # View coverage report
   ```

4. **Run specific test categories:**
   ```bash
   # Unit tests only
   pytest tests/unit/ -v
   
   # Integration tests only
   pytest tests/integration/ -v
   
   # Specific test file
   pytest tests/unit/test_denial_agent.py -v
   
   # Specific test function
   pytest tests/unit/test_denial_agent.py::TestDenialResolutionAgent::test_make_decision_coding_error -v
   ```

### Option 2: Using the Test Runner Script

```bash
# Run all tests
./run_tests.sh all

# Run specific category
./run_tests.sh unit
./run_tests.sh integration
./run_tests.sh coverage
```

### Option 3: Using Docker Compose (Full Stack Testing)

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **Wait for services to be healthy:**
   ```bash
   docker-compose ps
   ```

3. **Run tests against live services:**
   ```bash
   pytest tests/integration/ -v
   ```

4. **Test API manually:**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Create a claim
   curl -X POST http://localhost:8000/claims/ \
     -H "Content-Type: application/json" \
     -d '{
       "claim_number": "TEST-001",
       "provider_npi": "1234567890",
       "patient_id": "PAT-001",
       "payer_id": "PAY-001",
       "payer_type": "COMMERCIAL",
       "amount": 1000.00,
       "cpt_codes": ["99213"],
       "icd_codes": ["E11.9"],
       "service_date_from": "2024-01-15T10:00:00",
       "service_date_to": "2024-01-15T10:30:00"
     }'
   ```

## Verification Checklist

Use this checklist to verify everything is tested:

### ✅ Core Components
- [ ] State machine transitions work correctly
- [ ] Denial classifier normalizes categories
- [ ] Agent makes decisions with confidence scores
- [ ] Orchestrator executes decisions
- [ ] Outcome tracking records results

### ✅ API Endpoints
- [ ] `/claims/{id}/events` - Get events
- [ ] `/claims/{id}/denials` - Get/create denials
- [ ] `/claims/{id}/process-denial` - Process with agent
- [ ] `/claims/{id}/agent-decisions` - Get decisions
- [ ] `/claims/{id}/execute-decision/{id}` - Execute decision
- [ ] `/claims/{id}/override-decision/{id}` - Human override
- [ ] `/analytics/success-rates` - Analytics

### ✅ Workflow Scenarios
- [ ] Complete denial workflow (deny → classify → decide → execute)
- [ ] Human override works
- [ ] Low confidence flags for review
- [ ] Event logging captures everything
- [ ] Outcome tracking records results

## Viewing Test Results

### 1. Terminal Output
Tests show results in the terminal with:
- ✓ for passing tests
- ✗ for failing tests
- Test names and descriptions

### 2. Coverage Report
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

This shows:
- Which code is covered by tests
- Which lines are missing coverage
- Overall coverage percentage

### 3. Test Reports
```bash
# Generate JUnit XML report
pytest --junitxml=test-results.xml

# Generate HTML report (requires pytest-html)
pytest --html=report.html --self-contained-html
```

## Expected Test Counts

When you run tests, you should see approximately:

- **Unit Tests**: ~40+ tests
  - State machine: ~15 tests
  - Validator: ~15 tests
  - Classifier: ~10 tests
  - Agent: ~8 tests

- **Integration Tests**: ~15+ tests
  - API routes: ~10 tests
  - Celery tasks: ~5 tests
  - Denial workflow: ~8 tests

## Continuous Integration

For automated verification, add to your CI/CD:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Troubleshooting

### Tests won't run
```bash
# Check pytest is installed
pip install pytest

# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip install -r requirements.txt
```

### Import errors
```bash
# Make sure you're in the project directory
cd /path/to/RCM-Automation-Project

# Install in development mode
pip install -e .
```

### Database errors
Tests use in-memory SQLite, so no external database needed for unit tests.

## Quick Test Commands Reference

```bash
# Verify everything
python3 verify_tests.py

# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test
pytest tests/unit/test_denial_agent.py::TestDenialResolutionAgent::test_make_decision_coding_error -v

# Run and show print statements
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -x

# Run last failed tests
pytest --lf
```

## Success Indicators

You'll know tests are working when:

1. ✅ All test files exist
2. ✅ `pytest tests/` runs without errors
3. ✅ Coverage report shows >70% coverage
4. ✅ All API endpoints have tests
5. ✅ Integration tests pass with Docker Compose
6. ✅ No syntax errors in any file

## Next Steps

After verification:
1. Create database migrations: `alembic revision --autogenerate`
2. Deploy to staging
3. Run smoke tests
4. Monitor in production
