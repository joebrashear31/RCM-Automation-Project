# Agentic AI Denial Handling System

This document describes the automated denial handling system with agentic AI orchestration.

## Architecture Overview

```
Detect → Understand → Decide → Act → Learn
```

The system follows a **deterministic core with agentic decision-making** approach:
- **Backend is deterministic**: State machines, validation, execution
- **Agent makes decisions**: AI reasons about denials and recommends actions
- **System executes**: Backend carries out agent decisions
- **Learning loop**: Outcomes feed back to improve future decisions

## System Components

### PHASE 1: Deterministic Core ✅

#### 1. Enhanced State Machine
- **New States**: `REJECTED`, `APPEAL_PENDING`, `WRITE_OFF`
- **Valid Transitions**: Enforced at the service layer
- **Location**: `services/claims/state_machine.py`

**States:**
- `CREATED` → `VALIDATED` → `SUBMITTED`
- `SUBMITTED` → `REJECTED` (pre-adjudication) or `ACCEPTED` or `DENIED` (post-adjudication)
- `DENIED` → `APPEAL_PENDING` or `RESUBMITTED` or `WRITE_OFF`
- `APPEAL_PENDING` → `ACCEPTED` or `DENIED` or `WRITE_OFF`
- `RESUBMITTED` → `ACCEPTED` or `DENIED` or `REJECTED`
- `ACCEPTED` → `PAID` or `WRITE_OFF`

#### 2. Immutable Event Logging
- **`claim_events`**: All claim-related events with timestamps
- **`denial_events`**: Immutable denial records with full payer payload
- **Location**: `services/claims/models.py`

**Event Types:**
- `CLAIM_CREATED`, `CLAIM_VALIDATED`, `CLAIM_SUBMITTED`
- `CLAIM_REJECTED`, `CLAIM_DENIED`, `CLAIM_ACCEPTED`
- `DENIAL_CLASSIFIED`, `APPEAL_FILED`
- `AGENT_DECISION`, `HUMAN_OVERRIDE`, `WORKFLOW_EXECUTED`

**API Endpoints:**
- `GET /claims/{id}/events` - Get all events for a claim
- `GET /claims/{id}/denials` - Get all denial events

### PHASE 2: Deterministic Denial Classification ✅

#### 3. Normalized Denial Categories
Categories map raw payer codes to standardized concepts:

- **`ELIGIBILITY`**: Coverage terminated, COB required, invalid provider
- **`MEDICAL_NECESSITY`**: Not medically necessary
- **`CODING_ERROR`**: Invalid CPT/ICD codes
- **`PRIOR_AUTH_MISSING`**: Missing authorization
- **`TIMELY_FILING`**: Filed too late
- **`COVERAGE_EXHAUSTED`**: Benefits exhausted
- **`DUPLICATE`**: Duplicate claim
- **`DOCUMENTATION`**: Missing documentation
- **`UNKNOWN`**: Unclassified

**Location**: `common/enums.py` (DenialCategory enum)

#### 4. Rule-Based Recommended Actions
Deterministic baseline that agents can override:

```python
ELIGIBILITY → WRITE_OFF
CODING_ERROR → RESUBMIT
MEDICAL_NECESSITY → APPEAL
PRIOR_AUTH_MISSING → REQUEST_AUTH
TIMELY_FILING → WRITE_OFF
COVERAGE_EXHAUSTED → WRITE_OFF or COLLECT_PATIENT
DUPLICATE → NO_ACTION
```

**Location**: `services/denials/classifier.py` (`get_recommended_action()`)

### PHASE 3: Agent Decision-Making ✅

#### 5. Denial Resolution Agent
**Stateless decision-maker** - does NOT execute actions.

**Agent Inputs:**
- Claim data (amount, codes, dates)
- Denial category (normalized)
- Payer type
- Rule-based recommendation
- Historical success rates
- Payer history

**Agent Outputs:**
```json
{
  "decision": "appeal" | "resubmit" | "write_off" | "flag_for_human",
  "confidence": 0.82,
  "rationale": "Rule-based recommendation: APPEAL for MEDICAL_NECESSITY denial. Historical success rate (75%). High-value claim ($15,000.00), recommend careful review.",
  "missing_info": ["clinical_documentation"]
}
```

**Key Features:**
- Adjusts confidence based on historical data
- Flags missing information
- Considers claim value
- Category-specific reasoning logic

**Location**: `services/denials/agent.py`

#### 6. Agent Decision Audit Trail
**`agent_decisions` table** stores:
- Full decision (decision, confidence, rationale)
- Context (denial category, payer type, historical data)
- Execution status (was_executed, execution_result)
- Human interaction (override, reviewer, notes)
- Full prompt/response (for transparency)

**Location**: `services/claims/models.py` (AgentDecision model)

### PHASE 4: Agent-Driven Workflows ✅

#### 7. Workflow Orchestrator
Executes agent decisions and manages workflows.

**Flow:**
1. Denial received → Classify → Get rule-based recommendation
2. Agent evaluates → Makes decision
3. System checks confidence threshold
4. If high confidence → Auto-execute
5. If low confidence → Flag for human review
6. Human can override or approve

**Location**: `services/denials/orchestrator.py`

**API Endpoints:**
- `POST /claims/{id}/process-denial` - Process denial with agent
- `POST /claims/{id}/execute-decision/{decision_id}` - Execute agent decision
- `POST /claims/{id}/override-decision/{decision_id}` - Human override

#### 8. Human-in-the-Loop Controls
- **Confidence Threshold**: Default 0.7 (configurable)
- **Auto-execution**: Only for high-confidence decisions
- **Override Mechanism**: Humans can override any decision
- **Feedback Capture**: Human feedback stored for learning

**Configuration:**
```python
confidence_threshold: float = 0.7  # Minimum confidence for auto-execution
auto_execute: bool = False  # Whether to auto-execute high-confidence decisions
```

### PHASE 5: Learning Loop ✅

#### 9. Outcome Tracking
**`outcome_tracking` table** records:
- Action taken (resubmit, appeal, write_off, etc.)
- Outcome (SUCCESS, FAILURE, PENDING)
- Financial metrics (revenue recovered, time to resolution)
- Success flags (appeal_successful, resubmission_successful)
- Human feedback

**Location**: `services/denials/outcomes.py`

**Metrics Tracked:**
- Success rates by category/action
- Revenue recovery rates
- Time to resolution
- Appeal success rates
- Resubmission success rates

#### 10. Feedback Loop
- **Historical Success Rates**: Feed into agent decision-making
- **Learning Insights**: Analyze what works best for each category
- **Revenue Metrics**: Track overall recovery performance

**API Endpoints:**
- `GET /analytics/success-rates` - Get historical success rates
- `GET /analytics/revenue-metrics` - Get revenue recovery metrics
- `GET /analytics/learning-insights/{category}` - Get insights for category

**Location**: `services/claims/analytics_routes.py`

## Usage Examples

### 1. Create Denial Event and Process

```python
# Create denial event
POST /claims/{id}/denials
{
  "payer_id": "PAY-001",
  "payer_type": "COMMERCIAL",
  "denial_reason_code": "CO-50",
  "denial_reason_text": "Invalid CPT code",
  "raw_payer_payload": {...}
}

# Process with agent
POST /claims/{id}/process-denial?denial_category=CODING_ERROR&confidence_threshold=0.7&auto_execute=false

# Response: Agent decision with confidence and rationale
```

### 2. Execute Agent Decision

```python
# Execute decision (if not auto-executed)
POST /claims/{id}/execute-decision/{decision_id}

# Response: Execution result
```

### 3. Human Override

```python
# Override agent decision
POST /claims/{id}/override-decision/{decision_id}
{
  "override_action": "APPEAL",
  "reviewer": "john.doe@example.com",
  "notes": "Believe appeal has merit despite low confidence"
}
```

### 4. View Analytics

```python
# Get success rates
GET /analytics/success-rates?denial_category=CODING_ERROR&action_taken=RESUBMIT

# Get revenue metrics
GET /analytics/revenue-metrics?days_back=90

# Get learning insights
GET /analytics/learning-insights/CODING_ERROR?days_back=90
```

## Design Principles

1. **Deterministic Core First**: State machine and validation are rock-solid before adding AI
2. **Agent Decides, Backend Executes**: Clear separation of concerns
3. **Stateless Agent**: Agent never writes to DB directly
4. **Full Auditability**: Every decision logged with context
5. **Human-in-the-Loop**: Required for production deployments
6. **Learning Loop**: Outcomes improve future decisions
7. **Explainability**: Rationale stored for every decision
8. **Safety**: Low confidence → human review

## Future Enhancements

1. **LLM Integration**: Replace rule-based agent logic with LLM calls
2. **Fine-tuned Models**: Train models on historical outcomes
3. **Real-time Learning**: Update agent prompts based on recent outcomes
4. **Multi-agent System**: Different agents for different denial types
5. **Proactive Denial Prevention**: Predict and prevent denials before submission

## Testing

See `tests/` directory for comprehensive test coverage:
- Unit tests for state machine, classifier, agent
- Integration tests for API endpoints
- Docker Compose scenarios for end-to-end testing

Run tests:
```bash
pytest tests/
```
