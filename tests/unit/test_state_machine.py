"""Unit tests for claim state machine."""

import pytest
from common.enums import ClaimStatus
from services.claims.state_machine import ClaimStateMachine, StateMachineError
from services.claims.models import Claim, ClaimStateTransition
from datetime import datetime


class TestClaimStateMachine:
    """Test claim state transition logic."""

    def test_valid_transitions_from_created(self):
        """Test valid transitions from CREATED state."""
        valid_next = ClaimStateMachine.get_valid_next_states(ClaimStatus.CREATED)
        assert ClaimStatus.VALIDATED in valid_next
        assert len(valid_next) == 1

    def test_valid_transitions_from_validated(self):
        """Test valid transitions from VALIDATED state."""
        valid_next = ClaimStateMachine.get_valid_next_states(ClaimStatus.VALIDATED)
        assert ClaimStatus.SUBMITTED in valid_next
        assert len(valid_next) == 1

    def test_valid_transitions_from_submitted(self):
        """Test valid transitions from SUBMITTED state."""
        valid_next = ClaimStateMachine.get_valid_next_states(ClaimStatus.SUBMITTED)
        assert ClaimStatus.ACCEPTED in valid_next
        assert ClaimStatus.DENIED in valid_next
        assert len(valid_next) == 2

    def test_valid_transitions_from_accepted(self):
        """Test valid transitions from ACCEPTED state."""
        valid_next = ClaimStateMachine.get_valid_next_states(ClaimStatus.ACCEPTED)
        assert ClaimStatus.PAID in valid_next
        assert len(valid_next) == 1

    def test_valid_transitions_from_denied(self):
        """Test valid transitions from DENIED state."""
        valid_next = ClaimStateMachine.get_valid_next_states(ClaimStatus.DENIED)
        assert ClaimStatus.RESUBMITTED in valid_next
        assert len(valid_next) == 1

    def test_valid_transitions_from_resubmitted(self):
        """Test valid transitions from RESUBMITTED state."""
        valid_next = ClaimStateMachine.get_valid_next_states(ClaimStatus.RESUBMITTED)
        assert ClaimStatus.ACCEPTED in valid_next
        assert ClaimStatus.DENIED in valid_next
        assert len(valid_next) == 2

    def test_can_transition_created_to_validated(self):
        """Test that CREATED can transition to VALIDATED."""
        assert ClaimStateMachine.can_transition(ClaimStatus.CREATED, ClaimStatus.VALIDATED)

    def test_can_transition_validated_to_submitted(self):
        """Test that VALIDATED can transition to SUBMITTED."""
        assert ClaimStateMachine.can_transition(ClaimStatus.VALIDATED, ClaimStatus.SUBMITTED)

    def test_can_transition_submitted_to_accepted(self):
        """Test that SUBMITTED can transition to ACCEPTED."""
        assert ClaimStateMachine.can_transition(ClaimStatus.SUBMITTED, ClaimStatus.ACCEPTED)

    def test_can_transition_submitted_to_denied(self):
        """Test that SUBMITTED can transition to DENIED."""
        assert ClaimStateMachine.can_transition(ClaimStatus.SUBMITTED, ClaimStatus.DENIED)

    def test_cannot_transition_to_same_state(self):
        """Test that transitions to the same state are invalid."""
        assert not ClaimStateMachine.can_transition(ClaimStatus.CREATED, ClaimStatus.CREATED)
        assert not ClaimStateMachine.can_transition(ClaimStatus.SUBMITTED, ClaimStatus.SUBMITTED)

    def test_cannot_transition_invalid_path(self):
        """Test that invalid transition paths are rejected."""
        # Can't go directly from CREATED to SUBMITTED (must go through VALIDATED)
        assert not ClaimStateMachine.can_transition(ClaimStatus.CREATED, ClaimStatus.SUBMITTED)
        # Can't go from VALIDATED to DENIED (must go through SUBMITTED)
        assert not ClaimStateMachine.can_transition(ClaimStatus.VALIDATED, ClaimStatus.DENIED)
        # Can't go from ACCEPTED to DENIED
        assert not ClaimStateMachine.can_transition(ClaimStatus.ACCEPTED, ClaimStatus.DENIED)
        # Can't go from PAID to any other state
        valid_next = ClaimStateMachine.get_valid_next_states(ClaimStatus.PAID)
        assert len(valid_next) == 0

    def test_transition_creates_transition_record(self, db_session, sample_claim):
        """Test that transition creates an audit record."""
        claim = sample_claim
        assert claim.status == ClaimStatus.CREATED.value

        updated_claim, transition = ClaimStateMachine.transition(
            db=db_session,
            claim=claim,
            target_status=ClaimStatus.VALIDATED,
            reason="Test transition",
        )

        assert updated_claim.status == ClaimStatus.VALIDATED.value
        assert transition.from_status == ClaimStatus.CREATED.value
        assert transition.to_status == ClaimStatus.VALIDATED.value
        assert transition.transition_reason == "Test transition"

        # Verify transition was saved
        transitions = db_session.query(ClaimStateTransition).filter(
            ClaimStateTransition.claim_id == claim.id
        ).all()
        assert len(transitions) >= 1

    def test_transition_updates_timestamps(self, db_session, sample_claim):
        """Test that transition updates appropriate timestamps."""
        claim = sample_claim

        # Transition to SUBMITTED should set submitted_at
        updated_claim, _ = ClaimStateMachine.transition(
            db=db_session,
            claim=claim,
            target_status=ClaimStatus.VALIDATED,
            reason="Validate first",
        )
        
        updated_claim, _ = ClaimStateMachine.transition(
            db=db_session,
            claim=updated_claim,
            target_status=ClaimStatus.SUBMITTED,
            reason="Submit claim",
        )
        assert updated_claim.submitted_at is not None

        # Transition to ACCEPTED should set responded_at
        updated_claim, _ = ClaimStateMachine.transition(
            db=db_session,
            claim=updated_claim,
            target_status=ClaimStatus.ACCEPTED,
            reason="Claim accepted",
        )
        assert updated_claim.responded_at is not None

        # Transition to PAID should set paid_at
        updated_claim, _ = ClaimStateMachine.transition(
            db=db_session,
            claim=updated_claim,
            target_status=ClaimStatus.PAID,
            reason="Claim paid",
        )
        assert updated_claim.paid_at is not None

    def test_transition_raises_error_on_invalid_transition(self, db_session, sample_claim):
        """Test that invalid transitions raise StateMachineError."""
        claim = sample_claim

        with pytest.raises(StateMachineError) as exc_info:
            ClaimStateMachine.transition(
                db=db_session,
                claim=claim,
                target_status=ClaimStatus.PAID,  # Can't go directly from CREATED to PAID
                reason="Invalid transition",
            )

        assert "Cannot transition" in str(exc_info.value)

    def test_transition_denied_sets_responded_at(self, db_session, sample_claim):
        """Test that DENIED transition sets responded_at."""
        claim = sample_claim

        # Move through states to SUBMITTED
        claim, _ = ClaimStateMachine.transition(
            db=db_session, claim=claim, target_status=ClaimStatus.VALIDATED, reason="Validate"
        )
        claim, _ = ClaimStateMachine.transition(
            db=db_session, claim=claim, target_status=ClaimStatus.SUBMITTED, reason="Submit"
        )

        # Deny the claim
        claim, _ = ClaimStateMachine.transition(
            db=db_session, claim=claim, target_status=ClaimStatus.DENIED, reason="Denied"
        )
        assert claim.responded_at is not None
