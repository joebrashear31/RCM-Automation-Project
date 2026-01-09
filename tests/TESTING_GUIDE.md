# Testing Guide for RCM Workflow Engine

This guide explains how to test the RCM Workflow Engine for various scenarios.

## Overview

The test suite is organized into:
- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Tests for API endpoints and database interactions
- **Docker Scenarios**: End-to-end tests using Docker Compose

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_state_machine.py

# Specific test
pytest tests/unit/test_state_machine.py::TestClaimStateMachine::test_valid_transitions_from_created
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Run with Verbose Output

```bash
pytest -v
```

## Test Categories

### 1. Unit Tests (`tests/unit/`)

Fast, isolated tests that don't require external services.

#### State Machine Tests (`test_state_machine.py`)
- Valid state transitions
- Invalid transition rejection
- Timestamp updates
- Transition audit records

**Example**:
```bash
pytest tests/unit/test_state_machine.py -v
```

#### Validator Tests (`test_validator.py`)
- CPT code validation
- ICD code validation
- NPI validation
- Date range validation
- Payer-specific rules

**Example**:
```bash
pytest tests/unit/test_validator.py::TestValidateClaim::test_validate_claim_valid_commercial -v
```

#### Classifier Tests (`test_classifier.py`)
- Denial code classification
- Message-based classification
- Claim-specific classification

**Example**:
```bash
pytest tests/unit/test_classifier.py -v
```

### 2. Integration Tests (`tests/integration/`)

Tests that require database and API interactions.

#### API Route Tests (`test_api_routes.py`)
- Claim CRUD operations
- State transitions via API
- Error handling
- Full lifecycle workflows

**Example**:
```bash
pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_create_claim -v
```

#### Celery Task Tests (`test_celery_tasks.py`)
- Async task execution
- Validation tasks
- Denial classification tasks
- Error handling in tasks

**Example**:
```bash
pytest tests/integration/test_celery_tasks.py -v
```

### 3. Docker Compose Scenarios

See `tests/test_docker_scenarios.md` for detailed scenarios.

**Quick Start**:
```bash
# Start services
docker-compose up -d

# Run API tests against live services
pytest tests/integration/ -v

# Stop services
docker-compose down
```

## Common Test Scenarios

### Scenario 1: Happy Path - Successful Claim Processing

**Test**: `test_create_claim_full_lifecycle` in `test_api_routes.py`

1. Create claim
2. Validate claim
3. Submit to payer
4. Payer accepts
5. Payment received

**Run**:
```bash
pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_create_claim_full_lifecycle -v
```

### Scenario 2: Denial Workflow

**Test**: `test_denial_workflow` in `test_api_routes.py`

1. Create and submit claim
2. Payer denies claim
3. Classify denial reason
4. Resubmit claim
5. Claim accepted and paid

**Run**:
```bash
pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_denial_workflow -v
```

### Scenario 3: Invalid State Transitions

**Tests**: Multiple tests in `test_state_machine.py` and `test_api_routes.py`

- Attempt invalid transitions
- Verify errors are returned
- Verify state remains unchanged

**Run**:
```bash
pytest tests/unit/test_state_machine.py::TestClaimStateMachine::test_cannot_transition_invalid_path -v
pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_transition_claim_state_invalid -v
```

### Scenario 4: Payer-Specific Validation

**Tests**: `test_validate_medicare_rules`, `test_validate_medicaid_rules` in `test_validator.py`

- Medicare: Requires multiple ICD codes for certain CPTs
- Medicaid: High-value claims need authorization warnings
- Commercial: Standard validations

**Run**:
```bash
pytest tests/unit/test_validator.py::TestPayerRuleValidator::test_validate_medicare_rules -v
pytest tests/unit/test_validator.py::TestPayerRuleValidator::test_validate_medicaid_rules_high_value -v
```

### Scenario 5: Denial Classification

**Tests**: Multiple tests in `test_classifier.py`

- Classify by denial code (CO-50, CO-29, etc.)
- Classify by message text
- Combine code and message for higher confidence

**Run**:
```bash
pytest tests/unit/test_classifier.py::TestClassifyDenial -v
```

### Scenario 6: Concurrent Operations

**Test**: Load testing with Docker Compose (see `test_docker_scenarios.md`)

- Multiple concurrent claims
- Concurrent state transitions
- Verify no race conditions

### Scenario 7: Data Validation

**Tests**: Multiple tests in `test_validator.py`

- Invalid CPT codes
- Invalid ICD codes
- Invalid NPI format
- Invalid date ranges

**Run**:
```bash
pytest tests/unit/test_validator.py::TestPayerRuleValidator -v
```

## Test Fixtures

The test suite uses pytest fixtures for common setup:

- `db_session`: In-memory SQLite database session
- `client`: FastAPI test client
- `sample_claim_data`: Sample claim data dictionary
- `sample_claim`: Claim instance in database
- `medicare_claim_data`: Medicare-specific claim data
- `medicaid_claim_data`: Medicaid-specific claim data

## Writing New Tests

### Unit Test Example

```python
def test_my_feature(db_session, sample_claim):
    """Test description."""
    # Arrange
    claim = sample_claim
    
    # Act
    result = my_function(claim)
    
    # Assert
    assert result.status == "expected"
```

### Integration Test Example

```python
def test_my_api_endpoint(client, sample_claim_data):
    """Test API endpoint."""
    # Act
    response = client.post("/claims/", json=sample_claim_data)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["status"] == "CREATED"
```

## Debugging Tests

### Run Tests with Debugger

```bash
pytest --pdb tests/unit/test_state_machine.py
```

### Print Statements

```python
def test_something(db_session):
    claim = db_session.query(Claim).first()
    print(f"Claim status: {claim.status}")  # Will show in test output
    assert claim.status == "CREATED"
```

### Check Database State

```python
def test_with_db_check(db_session, sample_claim):
    # Check database state
    claims = db_session.query(Claim).all()
    print(f"Total claims: {len(claims)}")
    
    transitions = db_session.query(ClaimStateTransition).all()
    print(f"Total transitions: {len(transitions)}")
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Fixtures**: Use fixtures for common setup
3. **Naming**: Use descriptive test names
4. **Assertions**: Make specific assertions
5. **Cleanup**: Let fixtures handle cleanup (automatic with `scope="function"`)
6. **Mocking**: Mock external services (Celery, external APIs)
7. **Coverage**: Aim for >80% code coverage

## Troubleshooting

### Tests Fail with Import Errors

```bash
# Install in development mode
pip install -e .

# Or add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Errors

- Tests use in-memory SQLite, so no external database needed
- If issues persist, check `conftest.py` database setup

### Celery Task Tests Fail

- These tests mock Celery, so no Redis needed for unit tests
- For integration tests, ensure Redis is running or mock it

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/core/testing.html)
