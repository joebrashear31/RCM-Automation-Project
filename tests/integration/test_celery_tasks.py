"""Integration tests for Celery tasks."""

import pytest
from unittest.mock import patch, MagicMock
from services.claims.tasks import validate_claim_rules_task, classify_denial_task
from services.claims.models import Claim
from common.enums import ClaimStatus, PayerType, DenialReason
from datetime import datetime
from services.rules.validator import ValidationResult


class TestValidateClaimRulesTask:
    """Test the validate_claim_rules Celery task."""

    @patch("services.claims.tasks.validator.validate_claim")
    def test_validate_claim_rules_success(self, mock_validate, db_session, sample_claim):
        """Test successful claim validation task."""
        # Mock validation to return success
        mock_validate.return_value = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Minor warning"],
        )

        result = validate_claim_rules_task(sample_claim.id)

        assert result["status"] == "success"
        assert result["claim_id"] == sample_claim.id
        assert "warnings" in result

        # Verify claim was transitioned to VALIDATED
        db_session.refresh(sample_claim)
        assert sample_claim.status == ClaimStatus.VALIDATED.value

    @patch("services.claims.tasks.validator.validate_claim")
    def test_validate_claim_rules_failure(self, mock_validate, db_session, sample_claim):
        """Test failed claim validation task."""
        # Mock validation to return failure
        mock_validate.return_value = ValidationResult(
            is_valid=False,
            errors=["Invalid CPT code"],
            warnings=[],
        )

        result = validate_claim_rules_task(sample_claim.id)

        assert result["status"] == "failed"
        assert result["claim_id"] == sample_claim.id
        assert "errors" in result
        assert "Invalid CPT code" in result["errors"]

        # Verify claim status did NOT change
        db_session.refresh(sample_claim)
        assert sample_claim.status == ClaimStatus.CREATED.value

    def test_validate_claim_rules_claim_not_found(self, db_session):
        """Test validation task handles missing claim."""
        result = validate_claim_rules_task(99999)
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_validate_claim_rules_wrong_state(self, db_session, sample_claim):
        """Test validation task skips if claim is not in CREATED state."""
        # Move claim to VALIDATED state
        from services.claims.state_machine import ClaimStateMachine

        ClaimStateMachine.transition(
            db=db_session,
            claim=sample_claim,
            target_status=ClaimStatus.VALIDATED,
            reason="Test",
        )

        result = validate_claim_rules_task(sample_claim.id)
        assert result["status"] == "skipped"
        assert "not in CREATED state" in result["message"]


class TestClassifyDenialTask:
    """Test the classify_denial Celery task."""

    @patch("services.claims.tasks.classifier.classify_denial")
    def test_classify_denial_success(self, mock_classify, db_session, sample_claim):
        """Test successful denial classification task."""
        # Mock classification result
        from services.denials.classifier import DenialClassification

        mock_classify.return_value = DenialClassification(
            reason=DenialReason.INVALID_CPT_CODE,
            confidence=0.95,
            details="CPT code not covered by payer",
        )

        result = classify_denial_task(
            claim_id=sample_claim.id,
            denial_code="CO-50",
            denial_message="Invalid CPT code",
        )

        assert result["status"] == "success"
        assert result["claim_id"] == sample_claim.id
        assert result["denial_reason"] == DenialReason.INVALID_CPT_CODE.value
        assert result["confidence"] == 0.95

        # Verify claim was updated with denial info
        db_session.refresh(sample_claim)
        assert sample_claim.denial_reason == DenialReason.INVALID_CPT_CODE.value
        assert sample_claim.denial_details == "CPT code not covered by payer"

    def test_classify_denial_claim_not_found(self, db_session):
        """Test classification task handles missing claim."""
        result = classify_denial_task(
            claim_id=99999,
            denial_code="CO-50",
            denial_message="Test denial",
        )
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @patch("services.claims.tasks.classifier.classify_denial")
    def test_classify_denial_various_reasons(self, mock_classify, db_session, sample_claim):
        """Test classification of various denial reasons."""
        denial_scenarios = [
            (DenialReason.MISSING_AUTHORIZATION, "CO-29", "Prior authorization required", 0.9),
            (DenialReason.DUPLICATE_CLAIM, "CO-18", "Duplicate claim", 0.9),
            (DenialReason.COVERAGE_TERMINATED, "CO-11", "Coverage terminated", 0.9),
        ]

        for reason, code, message, confidence in denial_scenarios:
            from services.denials.classifier import DenialClassification

            mock_classify.return_value = DenialClassification(
                reason=reason,
                confidence=confidence,
                details=f"Classified as {reason.value}",
            )

            result = classify_denial_task(
                claim_id=sample_claim.id,
                denial_code=code,
                denial_message=message,
            )

            assert result["status"] == "success"
            assert result["denial_reason"] == reason.value

            # Refresh claim for next iteration
            db_session.refresh(sample_claim)
