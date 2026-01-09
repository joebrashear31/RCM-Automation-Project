"""FastAPI routes for claims management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from enum import Enum
from common.db import get_db
from common.enums import ClaimStatus, EventType, DenialCategory, AgentDecision as AgentDecisionEnum
from services.claims import models, schemas, state_machine

router = APIRouter(prefix="/claims", tags=["claims"])

# api router for creating a claim
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

# get transition history for a claim
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

# transition claim state
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


@router.get("/{claim_id}/events", response_model=List[schemas.ClaimEventResponse])
def get_claim_events(claim_id: int, db: Session = Depends(get_db)):
    """Get all events for a claim (immutable event log)."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    events = (
        db.query(models.ClaimEvent)
        .filter(models.ClaimEvent.claim_id == claim_id)
        .order_by(models.ClaimEvent.created_at)
        .all()
    )
    return events


@router.get("/{claim_id}/denials", response_model=List[schemas.DenialEventResponse])
def get_claim_denials(claim_id: int, db: Session = Depends(get_db)):
    """Get all denial events for a claim."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    denials = (
        db.query(models.DenialEvent)
        .filter(models.DenialEvent.claim_id == claim_id)
        .order_by(models.DenialEvent.created_at)
        .all()
    )
    return denials


@router.post("/{claim_id}/denials", response_model=schemas.DenialEventResponse, status_code=status.HTTP_201_CREATED)
def create_denial_event(
    claim_id: int,
    denial_event: schemas.DenialEventCreate,
    db: Session = Depends(get_db),
):
    """Create a denial event and classify it."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    # Classify the denial
    from services.denials.classifier import classify_denial
    from common.enums import PayerType

    classification = classify_denial(
        payer_type=PayerType(denial_event.payer_type),
        denial_code=denial_event.denial_reason_code,
        denial_message=denial_event.denial_reason_text,
        claim_data={
            "cpt_codes": claim.cpt_codes,
            "icd_codes": claim.icd_codes,
            "amount": float(claim.amount),
        },
    )

    # Get recommended action
    from services.denials.classifier import get_recommended_action

    recommended_action = get_recommended_action(classification.category)

    # Create denial event
    denial_event_db = models.DenialEvent(
        claim_id=claim_id,
        payer_id=denial_event.payer_id,
        payer_type=denial_event.payer_type,
        denial_reason_code=denial_event.denial_reason_code,
        denial_reason_text=denial_event.denial_reason_text,
        denial_category=classification.category.value if classification.category else None,
        raw_payer_payload=denial_event.raw_payer_payload,
        recommended_action=recommended_action.value if recommended_action else None,
        classification_confidence=classification.confidence,
    )

    # Create claim event
    claim_event = models.ClaimEvent(
        claim_id=claim_id,
        event_type=EventType.CLAIM_DENIED.value,
        event_data={
            "denial_reason_code": denial_event.denial_reason_code,
            "denial_category": classification.category.value if classification.category else None,
        },
        description=f"Claim denied: {denial_event.denial_reason_text}",
    )

    db.add(denial_event_db)
    db.add(claim_event)
    db.commit()
    db.refresh(denial_event_db)

    return denial_event_db


@router.get("/{claim_id}/agent-decisions", response_model=List[schemas.AgentDecisionResponse])
def get_agent_decisions(claim_id: int, db: Session = Depends(get_db)):
    """Get all agent decisions for a claim."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    decisions = (
        db.query(models.AgentDecision)
        .filter(models.AgentDecision.claim_id == claim_id)
        .order_by(models.AgentDecision.created_at)
        .all()
    )
    return decisions


@router.post("/{claim_id}/process-denial", response_model=schemas.AgentDecisionResponse)
def process_denial(
    claim_id: int,
    denial_category: DenialCategory,
    confidence_threshold: float = 0.7,
    auto_execute: bool = False,
    db: Session = Depends(get_db),
):
    """Process a denial with agent decision-making."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    from services.denials.orchestrator import WorkflowOrchestrator

    agent_decision, was_executed = WorkflowOrchestrator.process_denial(
        db=db,
        claim=claim,
        denial_category=denial_category,
        confidence_threshold=confidence_threshold,
        auto_execute=auto_execute,
    )

    return agent_decision


@router.post("/{claim_id}/execute-decision/{decision_id}")
def execute_agent_decision(
    claim_id: int,
    decision_id: int,
    db: Session = Depends(get_db),
):
    """Execute a previously made agent decision."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    from services.denials.orchestrator import WorkflowOrchestrator

    try:
        result = WorkflowOrchestrator.execute_agent_decision(
            db=db, claim=claim, agent_decision_id=decision_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{claim_id}/override-decision/{decision_id}")
def human_override_decision(
    claim_id: int,
    decision_id: int,
    override_request: schemas.HumanOverrideRequest,
    db: Session = Depends(get_db),
):
    """Human override of an agent decision."""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    from services.denials.orchestrator import WorkflowOrchestrator

    try:
        result = WorkflowOrchestrator.human_override(
            db=db,
            claim=claim,
            agent_decision_id=decision_id,
            override_action=override_request.override_action,
            reviewer=override_request.reviewer,
            notes=override_request.notes,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

