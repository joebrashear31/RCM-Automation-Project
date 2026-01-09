# Docker Compose Test Scenarios

This document outlines various testing scenarios for the RCM Workflow Engine using Docker Compose.

## Prerequisites

1. Docker and Docker Compose installed
2. All services defined in `docker-compose.yml`
3. Ports 5432, 6379, and 8000 available (or modify ports in docker-compose.yml)

## Quick Start

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat

# Stop all services
docker-compose down
```

## Test Scenarios

### Scenario 1: Basic Service Health Checks

**Goal**: Verify all services start correctly and are healthy.

**Steps**:
1. Start services: `docker-compose up -d`
2. Wait for health checks to pass (check logs)
3. Test API health endpoint: `curl http://localhost:8000/health`
4. Verify database connection: `docker-compose exec api python -c "from common.db import engine; engine.connect()"`

**Expected Results**:
- All services show as "healthy" or "running"
- API health endpoint returns `{"status": "healthy"}`
- No errors in service logs

---

### Scenario 2: Full Claim Lifecycle

**Goal**: Test complete claim processing workflow end-to-end.

**Steps**:
1. Start services: `docker-compose up -d`
2. Create a claim via API:
   ```bash
   curl -X POST http://localhost:8000/claims/ \
     -H "Content-Type: application/json" \
     -d '{
       "claim_number": "CLM-001",
       "provider_npi": "1234567890",
       "patient_id": "PAT-001",
       "payer_id": "PAY-001",
       "payer_type": "COMMERCIAL",
       "amount": 1000.00,
       "cpt_codes": ["99213", "36415"],
       "icd_codes": ["E11.9", "I10"],
       "service_date_from": "2024-01-15T10:00:00",
       "service_date_to": "2024-01-15T10:30:00"
     }'
   ```
3. Transition claim through states:
   - CREATED → VALIDATED
   - VALIDATED → SUBMITTED
   - SUBMITTED → ACCEPTED
   - ACCEPTED → PAID
4. Check transition history and timestamps

**Expected Results**:
- Claim created successfully
- Each transition succeeds
- Timestamps (`submitted_at`, `responded_at`, `paid_at`) are set correctly
- Transition audit trail is complete

---

### Scenario 3: Denial and Resubmission Workflow

**Goal**: Test claim denial and resubmission process.

**Steps**:
1. Create and submit a claim (as in Scenario 2)
2. Transition to DENIED:
   ```bash
   curl -X POST http://localhost:8000/claims/{claim_id}/transition \
     -H "Content-Type: application/json" \
     -d '{
       "target_status": "DENIED",
       "reason": "Denied by payer"
     }'
   ```
3. Update claim with denial details
4. Trigger denial classification task (via Celery)
5. Resubmit the claim
6. Transition from RESUBMITTED → ACCEPTED → PAID

**Expected Results**:
- Denial is recorded with proper reason
- Denial classification task runs successfully
- Claim can be resubmitted
- Resubmitted claim can be accepted and paid

---

### Scenario 4: Invalid State Transitions

**Goal**: Verify state machine enforces valid transitions.

**Steps**:
1. Create a claim
2. Attempt invalid transitions:
   - CREATED → PAID (should fail)
   - CREATED → DENIED (should fail)
   - ACCEPTED → DENIED (should fail)
3. Check error responses

**Expected Results**:
- All invalid transitions return 400 Bad Request
- Error messages indicate valid next states
- Claim status remains unchanged

---

### Scenario 5: Celery Background Task Processing

**Goal**: Test async task execution.

**Steps**:
1. Start services with Celery workers: `docker-compose up -d`
2. Create a claim
3. Trigger validation task via Celery (manually or via API integration)
4. Monitor Celery worker logs: `docker-compose logs -f celery-worker`
5. Verify claim transitions after task completion

**Expected Results**:
- Celery task is queued successfully
- Task executes in worker
- Claim status updates after task completion
- No task failures or errors

---

### Scenario 6: Database Persistence

**Goal**: Verify data persists across service restarts.

**Steps**:
1. Create several claims with various states
2. Stop services: `docker-compose down`
3. Restart services: `docker-compose up -d`
4. Query claims via API: `curl http://localhost:8000/claims/`
5. Verify all data is intact

**Expected Results**:
- All claims persist after restart
- Claim states are preserved
- Transition history is maintained
- No data loss

---

### Scenario 7: Service Failure Recovery

**Goal**: Test resilience to service failures.

**Steps**:
1. Start all services
2. Create and process claims
3. Stop a service (e.g., `docker-compose stop celery-worker`)
4. Attempt operations that require that service
5. Restart the service
6. Verify operations resume correctly

**Expected Results**:
- Services handle failures gracefully
- Queued tasks persist in Redis
- Services recover when restarted
- No data corruption

---

### Scenario 8: Load Testing

**Goal**: Test system under concurrent load.

**Steps**:
1. Use a load testing tool (e.g., `ab`, `wrk`, or `locust`)
2. Create multiple claims concurrently
3. Perform concurrent state transitions
4. Monitor service logs and resource usage

**Example Load Test**:
```bash
# Install Apache Bench if needed
# Create claims in parallel
for i in {1..100}; do
  curl -X POST http://localhost:8000/claims/ \
    -H "Content-Type: application/json" \
    -d "{...claim data with claim_number: CLM-$i...}" &
done
wait
```

**Expected Results**:
- System handles concurrent requests
- No deadlocks or data corruption
- Reasonable response times
- Services remain stable

---

### Scenario 9: Payer-Specific Validation

**Goal**: Test payer-specific validation rules.

**Steps**:
1. Create claims for each payer type:
   - Medicare
   - Medicaid
   - Commercial
   - Self-pay
2. Run validation on each claim
3. Verify payer-specific rules are applied

**Expected Results**:
- Medicare claims check for required ICD codes
- Medicaid high-value claims trigger warnings
- Each payer type has appropriate validations

---

### Scenario 10: Celery Beat Scheduled Tasks

**Goal**: Test scheduled periodic tasks (if configured).

**Steps**:
1. Monitor Celery Beat logs: `docker-compose logs -f celery-beat`
2. Verify scheduled tasks are queued at correct intervals
3. Check that workers process scheduled tasks

**Expected Results**:
- Tasks are scheduled correctly
- Tasks execute at specified intervals
- No missed or duplicate executions

---

## Monitoring and Debugging

### View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f celery-worker
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U rcm_user -d rcm_db

# List tables
\dt

# Query claims
SELECT * FROM claims;

# Query transitions
SELECT * FROM claim_state_transitions;
```

### Redis Access

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Monitor queue
KEYS *
LLEN celery

# View task queue
LRANGE celery 0 -1
```

### API Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# List claims
curl http://localhost:8000/claims/

# Get claim
curl http://localhost:8000/claims/1

# Create claim
curl -X POST http://localhost:8000/claims/ \
  -H "Content-Type: application/json" \
  -d '{...}'

# Transition claim
curl -X POST http://localhost:8000/claims/1/transition \
  -H "Content-Type: application/json" \
  -d '{"target_status": "VALIDATED", "reason": "Test"}'
```

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache
```

## Troubleshooting

### Services won't start
- Check port conflicts: `lsof -i :5432`, `lsof -i :6379`, `lsof -i :8000`
- Check Docker daemon: `docker ps`
- Review logs: `docker-compose logs`

### Database connection errors
- Verify PostgreSQL is healthy: `docker-compose ps postgres`
- Check DATABASE_URL environment variable
- Verify network connectivity between services

### Celery tasks not executing
- Check Redis is running: `docker-compose ps redis`
- Verify Celery worker is running: `docker-compose logs celery-worker`
- Check task queue in Redis: `docker-compose exec redis redis-cli LLEN celery`

### API errors
- Check API logs: `docker-compose logs -f api`
- Verify database migrations: `docker-compose exec api alembic current`
- Test database connection: `docker-compose exec api python -c "from common.db import engine; engine.connect()"`
