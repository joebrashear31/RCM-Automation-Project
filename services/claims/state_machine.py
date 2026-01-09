"""Claim state machine implementation."""

from typing import Optional, List, Tuple
from common.enums import ClaimStatus
from sqlalchemy.orm import Session
from services.claims.models import Claim, ClaimStateTransition
from datetime import datetime


class StateMachineError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


class ClaimStateMachine:
    """Enforces valid state transitions for claims."""

    # Define valid transitions as (from_status, to_status) tuples
    VALID_TRANSITIONS = [
        # Initial validation flow
        (ClaimStatus.CREATED, ClaimStatus.VALIDATED),
        (ClaimStatus.VALIDATED, ClaimStatus.SUBMITTED),
        
        # Submission outcomes
        (ClaimStatus.SUBMITTED, ClaimStatus.REJECTED),  # Pre-adjudication rejection
        (ClaimStatus.SUBMITTED, ClaimStatus.ACCEPTED),
        (ClaimStatus.SUBMITTED, ClaimStatus.DENIED),  # Post-adjudication denial
        
        # Rejection handling
        (ClaimStatus.REJECTED, ClaimStatus.RESUBMITTED),
        (ClaimStatus.REJECTED, ClaimStatus.WRITE_OFF),
        
        # Denial handling
        (ClaimStatus.DENIED, ClaimStatus.APPEAL_PENDING),
        (ClaimStatus.DENIED, ClaimStatus.RESUBMITTED),
        (ClaimStatus.DENIED, ClaimStatus.WRITE_OFF),
        
        # Appeal flow
        (ClaimStatus.APPEAL_PENDING, ClaimStatus.ACCEPTED),
        (ClaimStatus.APPEAL_PENDING, ClaimStatus.DENIED),
        (ClaimStatus.APPEAL_PENDING, ClaimStatus.WRITE_OFF),
        
        # Resubmission flow
        (ClaimStatus.RESUBMITTED, ClaimStatus.ACCEPTED),
        (ClaimStatus.RESUBMITTED, ClaimStatus.DENIED),
        (ClaimStatus.RESUBMITTED, ClaimStatus.REJECTED),
        
        # Payment and final states
        (ClaimStatus.ACCEPTED, ClaimStatus.PAID),
        (ClaimStatus.ACCEPTED, ClaimStatus.WRITE_OFF),  # In case of partial payment issues
    ]

    @classmethod
    def can_transition(cls, from_status: ClaimStatus, to_status: ClaimStatus) -> bool:
        """Check if a transition is valid."""
        if from_status == to_status:
            return False

        # Allow transitioning to any status from CREATED (initial state)
        if from_status == ClaimStatus.CREATED:
            return True

        return (from_status, to_status) in cls.VALID_TRANSITIONS

    @classmethod
    def get_valid_next_states(cls, current_status: ClaimStatus) -> List[ClaimStatus]:
        """Get all valid next states from current status."""
        if current_status == ClaimStatus.CREATED:
            return [ClaimStatus.VALIDATED]

        valid_states = [
            to_status
            for from_status, to_status in cls.VALID_TRANSITIONS
            if from_status == current_status
        ]
        return valid_states

    @classmethod
    def transition(
        cls,
        db: Session,
        claim: Claim,
        target_status: ClaimStatus,
        reason: Optional[str] = None,
    ) -> Tuple[Claim, ClaimStateTransition]:
        """
        Perform a state transition and record it in the audit trail.

        Raises StateMachineError if transition is invalid.
        """
        current_status = ClaimStatus(claim.status)

        if not cls.can_transition(current_status, target_status):
            raise StateMachineError(
                f"Cannot transition from {current_status.value} to {target_status.value}. "
                f"Valid next states: {[s.value for s in cls.get_valid_next_states(current_status)]}"
            )

        # Record transition
        transition = ClaimStateTransition(
            claim_id=claim.id,
            from_status=current_status.value,
            to_status=target_status.value,
            transition_reason=reason,
        )

        # Update claim status
        claim.status = target_status.value

        # Update timestamps based on status
        now = datetime.utcnow()
        if target_status == ClaimStatus.SUBMITTED:
            claim.submitted_at = now
        elif target_status in [ClaimStatus.ACCEPTED, ClaimStatus.DENIED, ClaimStatus.REJECTED]:
            claim.responded_at = now
        elif target_status == ClaimStatus.PAID:
            claim.paid_at = now

        db.add(transition)
        db.commit()
        db.refresh(claim)
        db.refresh(transition)

        return claim, transition

