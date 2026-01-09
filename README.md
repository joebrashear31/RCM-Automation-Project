# 🧾 RCM Workflow Engine

**Async, event-driven backend for medical claims lifecycle management with agentic AI denial automation**

The RCM Workflow Engine is a production-grade backend system that models the end-to-end revenue cycle management (RCM) process for healthcare providers. It focuses on claims state transitions, payer rule validation, and **intelligent automated denial handling** with agentic AI orchestration.

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [System Architecture](#-system-architecture)
- [Claim Lifecycle](#-claim-lifecycle)
- [Automated Denial Handling](#-automated-denial-handling)
- [Testing](#-testing)
- [API Reference](#-api-reference)
- [Development](#-development)
- [Tech Stack](#-tech-stack)

---

## 🚨 Problem Statement

Medical billing is one of the most complex and costly administrative processes in the U.S. healthcare system. Providers must navigate:

- Payer-specific billing rules
- Complex CPT / ICD code combinations
- Claim rejections vs denials
- Manual resubmissions and appeals
- Poor visibility into claim status and revenue leakage

As a result, healthcare organizations spend billions annually on administrative overhead just to get paid.

**This system automates denial handling with agentic AI: Detect → Understand → Decide → Act → Learn**

---

## ✨ Key Features

### Core Functionality
- ✅ **State-Based Claim Management** - Explicit state machine with enforced transitions
- ✅ **Payer Rule Validation** - Medicare, Medicaid, and Commercial payer-specific rules
- ✅ **Async Processing** - Celery workers for background tasks
- ✅ **Immutable Event Logging** - Complete audit trail for compliance

### Advanced Features
- 🤖 **Agentic AI Denial Resolution** - Intelligent decision-making for denial handling
- 📊 **Automated Denial Classification** - Normalized categories for better reasoning
- 🎯 **Rule-Based Recommendations** - Deterministic baseline for actions
- 👤 **Human-in-the-Loop** - Confidence thresholds and override mechanisms
- 📈 **Learning Loop** - Outcome tracking improves future decisions
- 💰 **Revenue Analytics** - Track recovery rates and success metrics

---

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for local development)

### Running with Docker Compose (Recommended)

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Check service status:**
   ```bash
   docker-compose ps
   ```

3. **View API documentation:**
   - Interactive Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

4. **View logs:**
   ```bash
   docker-compose logs -f api
   docker-compose logs -f celery-worker
   ```

### Create and Process a Claim

```bash
# 1. Create a claim
curl -X POST "http://localhost:8000/claims/" \
  -H "Content-Type: application/json" \
  -d '{
    "claim_number": "CLM-001",
    "provider_npi": "1234567890",
    "patient_id": "PAT-001",
    "payer_id": "PAYER-001",
    "payer_type": "COMMERCIAL",
    "amount": 1500.00,
    "cpt_codes": ["99213"],
    "icd_codes": ["E11.9"],
    "service_date_from": "2024-01-15T00:00:00",
    "service_date_to": "2024-01-15T00:00:00"
  }'

# 2. Transition to VALIDATED
curl -X POST "http://localhost:8000/claims/1/transition" \
  -H "Content-Type: application/json" \
  -d '{
    "target_status": "VALIDATED",
    "reason": "Payer rules validated"
  }'

# 3. Submit the claim
curl -X POST "http://localhost:8000/claims/1/transition" \
  -H "Content-Type: application/json" \
  -d '{
    "target_status": "SUBMITTED",
    "reason": "Submitted to payer"
  }'
```

### Local Development (without Docker)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export DATABASE_URL=postgresql://rcm_user:rcm_password@localhost:5432/rcm_db
   export REDIS_URL=redis://localhost:6379/0
   ```

3. **Start PostgreSQL and Redis:**
   ```bash
   docker-compose up -d postgres redis
   ```

4. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start the API:**
   ```bash
   uvicorn main:app --reload
   ```

6. **Start Celery worker (in another terminal):**
   ```bash
   celery -A common.celery_app worker --loglevel=info
   ```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (database data)
docker-compose down -v
```

---

## 🏗️ System Architecture

```
Client / API Consumer
        │
        ▼
 FastAPI Gateway
        │
        ▼
 Claims Service ──────► Postgres
        │
        ├──► Rules Engine (Validation)
        │
        ├──► Denials Engine (Classification)
        │
        ├──► Agent (Decision-Making) 🤖
        │
        └──► Orchestrator (Execution)
             │
             ▼
        Celery Workers ──────► Redis
```

### Design Philosophy

- **Explicit state over implicit logic** - State machine enforces valid transitions
- **Async-first** - Background processing for long-running workflows
- **Domain-driven modeling** - Healthcare finance as a first-class concern
- **Deterministic core, agentic decisions** - Backend is solid, AI makes decisions
- **Full auditability** - Every action is logged and traceable

---

## 🔄 Claim Lifecycle

Each medical claim is modeled as a finite state machine with explicit transitions:

```
CREATED
  ↓
VALIDATED
  ↓
SUBMITTED
  ↓
  ├──► ACCEPTED ──► PAID
  │
  ├──► REJECTED (pre-adjudication)
  │     └──► RESUBMITTED
  │
  └──► DENIED (post-adjudication)
        ├──► APPEAL_PENDING ──► ACCEPTED / DENIED / WRITE_OFF
        ├──► RESUBMITTED ──► ACCEPTED / DENIED / REJECTED
        └──► WRITE_OFF
```

### State Definitions

- **CREATED** - Initial claim created
- **VALIDATED** - Payer rules validated
- **SUBMITTED** - Sent to payer
- **REJECTED** - Pre-adjudication rejection (can fix and resubmit)
- **ACCEPTED** - Payer accepted claim
- **DENIED** - Post-adjudication denial (requires decision)
- **APPEAL_PENDING** - Appeal filed
- **RESUBMITTED** - Resubmitted after fix
- **PAID** - Payment received
- **WRITE_OFF** - Written off as uncollectible

State transitions are explicitly enforced at the service layer to ensure data integrity and auditability.

---

## 🤖 Automated Denial Handling

The system uses **agentic AI** to automate denial resolution decisions. The architecture follows: **Detect → Understand → Decide → Act → Learn**

### How It Works

1. **Detect** - Claim is denied by payer
2. **Understand** - Classify denial into normalized category (CODING_ERROR, ELIGIBILITY, etc.)
3. **Decide** - Agent evaluates and recommends action with confidence score
4. **Act** - System executes decision (or flags for human review)
5. **Learn** - Outcomes tracked to improve future decisions

### Denial Categories

Denials are normalized into standardized categories:

- **ELIGIBILITY** - Coverage terminated, COB required, invalid provider
- **MEDICAL_NECESSITY** - Not medically necessary
- **CODING_ERROR** - Invalid CPT/ICD codes
- **PRIOR_AUTH_MISSING** - Missing authorization
- **TIMELY_FILING** - Filed too late
- **COVERAGE_EXHAUSTED** - Benefits exhausted
- **DUPLICATE** - Duplicate claim
- **DOCUMENTATION** - Missing documentation
- **UNKNOWN** - Unclassified

### Rule-Based Recommendations

Before AI, the system uses deterministic rules:

```python
ELIGIBILITY → WRITE_OFF
CODING_ERROR → RESUBMIT
MEDICAL_NECESSITY → APPEAL
PRIOR_AUTH_MISSING → REQUEST_AUTH
TIMELY_FILING → WRITE_OFF
COVERAGE_EXHAUSTED → WRITE_OFF or COLLECT_PATIENT
DUPLICATE → NO_ACTION
```

### Agent Decision-Making

The agent (stateless decision-maker) evaluates:

- Claim data (amount, codes, dates)
- Denial category
- Historical success rates
- Missing information
- Claim value

**Output:**
```json
{
  "decision": "APPEAL" | "RESUBMIT" | "WRITE_OFF" | "FLAG_FOR_HUMAN",
  "confidence": 0.82,
  "rationale": "Rule-based recommendation: APPEAL for MEDICAL_NECESSITY...",
  "missing_info": ["clinical_documentation"]
}
```

### Human-in-the-Loop

- **Confidence Threshold** - Default 0.7 (configurable)
- **Auto-execution** - Only for high-confidence decisions
- **Override Mechanism** - Humans can override any decision
- **Full Audit Trail** - Every decision logged with context

### Example Workflow

```bash
# 1. Create denial event
POST /claims/{id}/denials
{
  "payer_id": "PAY-001",
  "payer_type": "COMMERCIAL",
  "denial_reason_code": "CO-50",
  "denial_reason_text": "Invalid CPT code"
}

# 2. Process with agent
POST /claims/{id}/process-denial?denial_category=CODING_ERROR&confidence_threshold=0.7

# Response: Agent decision
{
  "decision": "RESUBMIT",
  "confidence": 0.85,
  "rationale": "Coding errors can typically be corrected and resubmitted."
}

# 3. Execute decision (if not auto-executed)
POST /claims/{id}/execute-decision/{decision_id}

# 4. Track outcome (automatic)
# System records success/failure for learning loop
```

### Analytics & Learning

View insights and metrics:

```bash
# Success rates
GET /analytics/success-rates?denial_category=CODING_ERROR&action_taken=RESUBMIT

# Revenue metrics
GET /analytics/revenue-metrics?days_back=90

# Learning insights
GET /analytics/learning-insights/CODING_ERROR?days_back=90
```

---

## 🧪 Testing

### Quick Verification

Run the verification script to check everything is set up correctly:

```bash
python3 verify_tests.py
```

This will verify:
- ✅ All test files exist (11 test files, 93+ test functions)
- ✅ Code structure is correct
- ✅ Python syntax is valid
- ✅ Test configuration is present

### Running Tests

**Install dependencies first:**
```bash
pip install -r requirements.txt
```

**Run all tests:**
```bash
pytest tests/ -v
```

**Run with coverage:**
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
open htmlcov/index.html  # View coverage report
```

### Test Categories

**Unit Tests (Fast, no external services):**
```bash
# All unit tests
pytest tests/unit/ -v

# Specific components
pytest tests/unit/test_state_machine.py
pytest tests/unit/test_validator.py
pytest tests/unit/test_classifier.py
pytest tests/unit/test_denial_agent.py
```

**Integration Tests (Requires database):**
```bash
# All integration tests
pytest tests/integration/ -v

# Specific components
pytest tests/integration/test_api_routes.py
pytest tests/integration/test_celery_tasks.py
pytest tests/integration/test_denial_workflow.py
```

### Using the Test Runner Script

```bash
# All tests
./run_tests.sh all

# Specific categories
./run_tests.sh unit
./run_tests.sh integration
./run_tests.sh coverage

# Specific components
./run_tests.sh state-machine
./run_tests.sh validator
./run_tests.sh classifier
./run_tests.sh api
./run_tests.sh celery
```

### Test Coverage

The test suite includes:
- ✅ **State Machine**: All valid/invalid transitions tested
- ✅ **Validator**: CPT, ICD, NPI, payer-specific rules
- ✅ **Classifier**: Denial code and message classification
- ✅ **Agent**: Decision-making logic with confidence scoring
- ✅ **API Routes**: All endpoints tested
- ✅ **Workflows**: Complete end-to-end scenarios
- ✅ **Celery Tasks**: Background processing tested

**Current Coverage**: 93+ test functions across 11 test files

### Test Scenarios

**Happy Path:**
```bash
# Complete claim lifecycle
pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_create_claim_full_lifecycle

# Denial and resubmission
pytest tests/integration/test_api_routes.py::TestClaimRoutes::test_denial_workflow
```

**Validation:**
```bash
# CPT/ICD validation
pytest tests/unit/test_validator.py::TestPayerRuleValidator::test_validate_cpt_codes_invalid_format

# Payer-specific rules
pytest tests/unit/test_validator.py::TestPayerRuleValidator::test_validate_medicare_rules
```

**Agent Decision-Making:**
```bash
# Agent decisions
pytest tests/unit/test_denial_agent.py::TestDenialResolutionAgent::test_make_decision_coding_error

# Complete denial workflow
pytest tests/integration/test_denial_workflow.py::TestDenialWorkflow::test_complete_denial_workflow
```

### Debugging Tests

```bash
# Run with debugger
pytest --pdb tests/unit/test_state_machine.py

# Verbose output
pytest -v -vv

# Show print statements
pytest -s tests/unit/test_state_machine.py

# Stop on first failure
pytest -x
```

---

## 📚 API Reference

### Claims Management

- `POST /claims/` - Create a new claim
- `GET /claims/` - List all claims (with optional status filter)
- `GET /claims/{claim_id}` - Get claim details
- `PATCH /claims/{claim_id}` - Update claim fields
- `POST /claims/{claim_id}/transition` - Transition claim to new state
- `GET /claims/{claim_id}/transitions` - Get state transition history
- `GET /claims/{claim_id}/next-states` - Get valid next states

### Denial Handling

- `POST /claims/{claim_id}/denials` - Create denial event
- `GET /claims/{claim_id}/denials` - Get all denial events
- `POST /claims/{claim_id}/process-denial` - Process denial with agent
- `GET /claims/{claim_id}/agent-decisions` - Get agent decisions
- `POST /claims/{claim_id}/execute-decision/{decision_id}` - Execute agent decision
- `POST /claims/{claim_id}/override-decision/{decision_id}` - Human override

### Event Logging

- `GET /claims/{claim_id}/events` - Get all events for a claim

### Analytics

- `GET /analytics/success-rates` - Get historical success rates
- `GET /analytics/revenue-metrics` - Get revenue recovery metrics
- `GET /analytics/learning-insights/{category}` - Get insights for category

### System

- `GET /health` - Service health status
- `GET /` - Service info

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 💻 Development

### Project Structure

```
RCM-Automation-Project/
│
├── services/
│   ├── claims/
│   │   ├── models.py          # Database models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── routes.py          # API endpoints
│   │   ├── state_machine.py   # State transition logic
│   │   └── tasks.py           # Celery tasks
│   │
│   ├── denials/
│   │   ├── classifier.py      # Denial classification
│   │   ├── agent.py           # Agent decision-maker 🤖
│   │   ├── orchestrator.py    # Workflow orchestration
│   │   ├── outcomes.py        # Outcome tracking
│   │   └── tasks.py           # Celery tasks
│   │
│   └── rules/
│       └── validator.py       # Payer rule validation
│
├── common/
│   ├── db.py                  # Database configuration
│   ├── celery_app.py          # Celery app
│   └── enums.py               # Enumerations
│
├── tests/
│   ├── unit/                  # Unit tests (93+ tests)
│   ├── integration/           # Integration tests
│   ├── conftest.py            # Test fixtures
│   └── test_docker_scenarios.md
│
├── alembic/                   # Database migrations
├── docker-compose.yml         # Docker services
├── requirements.txt           # Python dependencies
└── main.py                    # FastAPI application
```

### Database Migrations

```bash
# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Or locally
alembic upgrade head
```

### Background Tasks

The system includes Celery workers for async processing:

- **`validate_claim_rules`** - Validates claims against payer rules
- **`classify_denial`** - Classifies denial reasons when claims are denied

Tasks are automatically triggered based on claim state transitions.

---

## 🧱 Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - Modern web framework
- **Pydantic v2** - Data validation
- **SQLAlchemy 2.0** - ORM
- **Celery** - Async task queue
- **PostgreSQL** - Database
- **Redis** - Task broker and cache

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **Alembic** - Database migrations
- **pytest** - Testing framework
- **Structured logging** - Application logging

### Testing
- **pytest** - Test framework
- **pytest-cov** - Coverage reporting
- **httpx** - HTTP client for testing
- **faker** - Test data generation

---

## 📊 Current Status

✅ **Completed Features:**
- Claim state machine with full lifecycle
- Payer rule validation (Medicare, Medicaid, Commercial)
- Denial classification with normalized categories
- Agentic AI denial resolution
- Workflow orchestration
- Human-in-the-loop controls
- Outcome tracking and learning loop
- Revenue analytics
- Comprehensive test suite (93+ tests)

🚧 **In Development:**
- LLM integration for enhanced agent reasoning
- Fine-tuned models based on historical data
- Proactive denial prevention

---

## 🛣️ Roadmap

- [ ] Enhanced agent reasoning with LLM integration
- [ ] Fine-tuned models for denial prediction
- [ ] Real-time learning from outcomes
- [ ] Multi-agent system for specialized denial types
- [ ] Proactive denial prevention before submission
- [ ] Advanced analytics dashboards

---

## 📜 Disclaimer

This project is for educational and demonstration purposes only. It does not process real patient data and is not intended for production use without proper security, compliance, and regulatory review.

---

## 📖 Additional Documentation

- **Quick Start**: See examples above
- **Testing Guide**: `tests/TESTING_GUIDE.md`
- **Docker Scenarios**: `tests/test_docker_scenarios.md`
- **Agentic Denial Handling**: Detailed architecture in code comments

---

## 🤝 Contributing

This is a demonstration project. For questions or improvements:
1. Review the code structure
2. Check test coverage
3. Follow existing patterns
4. Add tests for new features

---

## 📝 License

See LICENSE file for details.

---

**Built with ❤️ for healthcare revenue cycle management - by joemama**
