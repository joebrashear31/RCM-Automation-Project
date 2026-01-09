# Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for local development)

## Running with Docker Compose

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Check service status:**
   ```bash
   docker-compose ps
   ```

3. **View API documentation:**
   - Open http://localhost:8000/docs in your browser
   - Interactive Swagger UI available at http://localhost:8000/docs
   - ReDoc available at http://localhost:8000/redoc

4. **View logs:**
   ```bash
   docker-compose logs -f api
   docker-compose logs -f celery-worker
   ```

## API Endpoints

### Claims Management

- `POST /claims/` - Create a new claim
- `GET /claims/` - List all claims (with optional status filter)
- `GET /claims/{claim_id}` - Get claim details
- `POST /claims/{claim_id}/transition` - Transition claim to new state
- `GET /claims/{claim_id}/transitions` - Get state transition history
- `GET /claims/{claim_id}/next-states` - Get valid next states
- `PATCH /claims/{claim_id}` - Update claim fields

### Health Check

- `GET /health` - Service health status
- `GET /` - Service info

## Example: Creating and Processing a Claim

```bash
# 1. Create a claim
curl -X POST "http://localhost:8000/claims/" \
  -H "Content-Type: application/json" \
  -d '{
    "claim_number": "CLM-001",
    "provider_npi": "1234567890",
    "patient_id": "PAT-001",
    "payer_id": "PAYER-001",
    "payer_type": "MEDICARE",
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

## Background Tasks

The system includes Celery workers for async processing:

- **validate_claim_rules**: Validates claims against payer rules
- **classify_denial**: Classifies denial reasons when claims are denied

Tasks are automatically triggered based on claim state transitions.

## Database Migrations

To create a new migration:

```bash
docker-compose exec api alembic revision --autogenerate -m "description"
docker-compose exec api alembic upgrade head
```

## Local Development (without Docker)

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
   # Use Docker for just the databases
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

## Testing the State Machine

```bash
# Get valid next states for a claim
curl "http://localhost:8000/claims/1/next-states"

# View state transition history
curl "http://localhost:8000/claims/1/transitions"
```

## Stopping Services

```bash
docker-compose down
```

To also remove volumes (database data):
```bash
docker-compose down -v
```

