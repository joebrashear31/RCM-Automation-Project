# Testing Quick Reference

Quick commands and scenarios for testing the RCM Workflow Engine.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Or use the test runner script
./run_tests.sh all
```

## Common Test Commands

### Run Test Categories

```bash
# Unit tests only (fast, no external services)
pytest tests/unit/

# Integration tests (requires database)
pytest tests/integration/

# Specific component
pytest tests/unit/test_state_machine.py
pytest tests/unit/test_validator.py
pytest tests/unit/test_classifier.py
pytest tests/integration/test_api_routes.py
pytest tests/integration/test_celery_tasks.py
```

### Using Test Runner Script

```bash
# All tests
./run_tests.sh all

# Unit tests
./run_tests.sh unit

# Integration tests
./run_tests.sh integration

# Specific components
./run_tests.sh state-machine
./run_tests.sh validator
./run_tests.sh classifier
./run_tests.sh api
./run_tests.sh celery

# With coverage
./run_tests.sh coverage
```

### With Coverage

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Test Scenarios Overview

### ✅ Happy Path Scenarios

1. **Complete Claim Lifecycle**
   ```bash
   pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_create_claim_full_lifecycle
   ```
   - Create → Validate → Submit → Accept → Pay

2. **Denial and Resubmission**
   ```bash
   pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_denial_workflow
   ```
   - Submit → Deny → Classify → Resubmit → Accept → Pay

### ✅ Validation Scenarios

3. **CPT Code Validation**
   ```bash
   pytest tests/unit/test_validator.py::TestPayerRuleValidator::test_validate_cpt_codes_invalid_format
   ```

4. **ICD Code Validation**
   ```bash
   pytest tests/unit/test_validator.py::TestPayerRuleValidator::test_validate_icd_codes_invalid_format
   ```

5. **NPI Validation**
   ```bash
   pytest tests/unit/test_validator.py::TestPayerRuleValidator::test_validate_provider_npi_invalid_length
   ```

6. **Payer-Specific Rules**
   ```bash
   pytest tests/unit/test_validator.py::TestPayerRuleValidator::test_validate_medicare_rules
   pytest tests/unit/test_validator.py::TestPayerRuleValidator::test_validate_medicaid_rules_high_value
   ```

### ✅ State Machine Scenarios

7. **Valid Transitions**
   ```bash
   pytest tests/unit/test_state_machine.py::TestClaimStateMachine::test_valid_transitions_from_submitted
   ```

8. **Invalid Transitions**
   ```bash
   pytest tests/unit/test_state_machine.py::TestClaimStateMachine::test_cannot_transition_invalid_path
   pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_transition_claim_state_invalid
   ```

9. **Timestamp Updates**
   ```bash
   pytest tests/unit/test_state_machine.py::TestClaimStateMachine::test_transition_updates_timestamps
   ```

### ✅ Denial Classification Scenarios

10. **Classify by Code**
    ```bash
    pytest tests/unit/test_classifier.py::TestDenialClassifier::test_classify_by_code_invalid_cpt
    ```

11. **Classify by Message**
    ```bash
    pytest tests/unit/test_classifier.py::TestDenialClassifier::test_classify_by_message_invalid_cpt
    ```

12. **Combined Classification**
    ```bash
    pytest tests/unit/test_classifier.py::TestClassifyDenial::test_classify_denial_with_code
    ```

### ✅ API Scenarios

13. **Create Claim**
    ```bash
    pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_create_claim
    ```

14. **Duplicate Prevention**
    ```bash
    pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_create_claim_duplicate_claim_number
    ```

15. **List and Filter**
    ```bash
    pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_list_claims_with_status_filter
    ```

16. **Get Valid Next States**
    ```bash
    pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_get_valid_next_states
    ```

### ✅ Celery Task Scenarios

17. **Validation Task Success**
    ```bash
    pytest tests/integration/test_celery_tasks.py::TestValidateClaimRulesTask::test_validate_claim_rules_success
    ```

18. **Validation Task Failure**
    ```bash
    pytest tests/integration/test_celery_tasks.py::TestValidateClaimRulesTask::test_validate_claim_rules_failure
    ```

19. **Denial Classification Task**
    ```bash
    pytest tests/integration/test_celery_tasks.py::TestClassifyDenialTask::test_classify_denial_success
    ```

## Docker Compose Scenarios

For end-to-end testing with real services:

```bash
# Start all services
docker-compose up -d

# Test API against live services
curl http://localhost:8000/health
curl http://localhost:8000/claims/

# Stop services
docker-compose down
```

See `tests/test_docker_scenarios.md` for detailed Docker scenarios.

## Debugging

### Run with Debugger
```bash
pytest --pdb tests/unit/test_state_machine.py
```

### Verbose Output
```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run Specific Test
```bash
pytest tests/unit/test_state_machine.py::TestClaimStateMachine::test_valid_transitions_from_created -v
```

### Show Print Statements
```bash
pytest -s tests/unit/test_state_machine.py
```

## Test Coverage Goals

- **Unit Tests**: >90% coverage
- **Integration Tests**: Critical paths covered
- **State Machine**: 100% transition coverage
- **Validators**: All validation rules tested
- **Classifiers**: All denial types tested

## Files Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests (fast, isolated)
│   ├── test_state_machine.py
│   ├── test_validator.py
│   └── test_classifier.py
├── integration/                # Integration tests (require DB)
│   ├── test_api_routes.py
│   └── test_celery_tasks.py
├── TESTING_GUIDE.md           # Detailed testing guide
└── test_docker_scenarios.md   # Docker Compose scenarios
```

## Need Help?

- See `tests/TESTING_GUIDE.md` for detailed documentation
- See `tests/test_docker_scenarios.md` for Docker scenarios
- Check pytest output for specific error messages
- Use `pytest --pdb` to debug failing tests
