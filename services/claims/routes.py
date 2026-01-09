"""FastAPI routes for claims management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from enum import Enum
from common.db import get_db
from common.enums import ClaimStatus
from services.claims import models, schemas, state_machine

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("/", response_model=schemas.ClaimResponse, status_code=status.HTTP_201_CREATED)
def create_claim(claim: schemas.ClaimCreate, db: Session = Depends(get_db)):
    """Create a new claim in CREATED state."""
    # Check if claim number already exists
    existing = db.query(models.Claim).filter(models.Claim.claim_number == claim.claim_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Claim with number {claim.claim_number} already exists",
        )

    db_claim = models.Claim(
        claim_number=claim.claim_number,
        provider_npi=claim.provider_npi,
        patient_id=claim.patient_id,
        payer_id=claim.payer_id,
        payer_type=claim.payer_type.value,
        amount=claim.amount,
        cpt_codes=claim.cpt_codes,
        icd_codes=claim.icd_codes,
        service_date_from=claim.service_date_from,
        service_date_to=claim.service_date_to,
        status=ClaimStatus.CREATED.value,
    )

    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)

    # Create initial state transition record
    transition = models.ClaimStateTransition(
        claim_id=db_claim.id,
        from_status=None,
        to_status=ClaimStatus.CREATED.value,
        transition_reason="Initial claim creation",
    )
    db.add(transition)
    db.commit()

    return db_claim


@router.get("/", response_model=List[schemas.ClaimResponse])
def list_claims(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[ClaimStatus] = None,
    db: Session = Depends(get_db),
):
    """List claims with optional status filter."""
    query = db.query(models.Claim)

    if status_filter:
        query = query.filter(models.Claim.status == status_filter.value)

    claims = query.offset(skip).limit(limit).all()
    return claims


@router.get("/{claim_id}", response_model=schemas.ClaimResponse)
def get_claim(claim_id: int, db: Session = Depends(get_db)):
    """Get a single claim by ID."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.get("/{claim_id}/transitions", response_model=List[schemas.ClaimStateTransitionResponse])
def get_claim_transitions(claim_id: int, db: Session = Depends(get_db)):
    """Get state transition history for a claim."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    transitions = (
        db.query(models.ClaimStateTransition)
        .filter(models.ClaimStateTransition.claim_id == claim_id)
        .order_by(models.ClaimStateTransition.created_at)
        .all()
    )
    return transitions


@router.post("/{claim_id}/transition", response_model=schemas.ClaimResponse)
def transition_claim_state(
    claim_id: int,
    transition: schemas.StateTransitionRequest,
    db: Session = Depends(get_db),
):
    """Transition a claim to a new state."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    try:
        updated_claim, _ = state_machine.ClaimStateMachine.transition(
            db=db, claim=claim, target_status=transition.target_status, reason=transition.reason
        )
        return updated_claim
    except state_machine.StateMachineError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{claim_id}", response_model=schemas.ClaimResponse)
def update_claim(
    claim_id: int,
    claim_update: schemas.ClaimUpdate,
    db: Session = Depends(get_db),
):
    """Update claim fields (limited to non-state fields)."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    update_data = claim_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(claim, field):
            setattr(claim, field, value.value if isinstance(value, Enum) else value)

    db.commit()
    db.refresh(claim)
    return claim


@router.get("/{claim_id}/next-states", response_model=List[str])
def get_valid_next_states(claim_id: int, db: Session = Depends(get_db)):
    """Get valid next states for a claim."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    current_status = ClaimStatus(claim.status)
    next_states = state_machine.ClaimStateMachine.get_valid_next_states(current_status)
    return [state.value for state in next_states]

