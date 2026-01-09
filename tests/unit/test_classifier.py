"""Unit tests for denial classifier."""

import pytest
from services.denials.classifier import DenialClassifier, classify_denial
from common.enums import DenialReason, PayerType


class TestDenialClassifier:
    """Test denial classification logic."""

    def test_classify_by_code_invalid_cpt(self):
        """Test classification of invalid CPT code denial."""
        result = DenialClassifier.classify_by_code("CO-50", PayerType.COMMERCIAL)
        assert result.reason == DenialReason.INVALID_CPT_CODE
        assert result.confidence >= 0.9

    def test_classify_by_code_invalid_icd(self):
        """Test classification of invalid ICD code denial."""
        result = DenialClassifier.classify_by_code("CO-19", PayerType.MEDICARE)
        assert result.reason == DenialReason.INVALID_ICD_CODE
        assert result.confidence >= 0.9

    def test_classify_by_code_missing_authorization(self):
        """Test classification of missing authorization denial."""
        result = DenialClassifier.classify_by_code("CO-29", PayerType.COMMERCIAL)
        assert result.reason == DenialReason.MISSING_AUTHORIZATION
        assert result.confidence >= 0.9

    def test_classify_by_code_duplicate_claim(self):
        """Test classification of duplicate claim denial."""
        result = DenialClassifier.classify_by_code("CO-18", PayerType.MEDICAID)
        assert result.reason == DenialReason.DUPLICATE_CLAIM
        assert result.confidence >= 0.9

    def test_classify_by_code_unknown(self):
        """Test classification of unknown denial code."""
        result = DenialClassifier.classify_by_code("CO-999", PayerType.COMMERCIAL)
        assert result.reason == DenialReason.UNKNOWN
        assert result.confidence < 0.5

    def test_classify_by_message_invalid_cpt(self):
        """Test classification from message text for invalid CPT."""
        message = "Invalid CPT code or procedure code not covered"
        result = DenialClassifier.classify_by_message(message, PayerType.COMMERCIAL)
        assert result.reason == DenialReason.INVALID_CPT_CODE
        assert result.confidence > 0.0

    def test_classify_by_message_missing_authorization(self):
        """Test classification from message for missing authorization."""
        message = "Prior authorization required for this procedure"
        result = DenialClassifier.classify_by_message(message, PayerType.COMMERCIAL)
        assert result.reason == DenialReason.MISSING_AUTHORIZATION
        assert result.confidence > 0.0

    def test_classify_by_message_duplicate(self):
        """Test classification from message for duplicate claim."""
        message = "This claim is a duplicate and was already processed"
        result = DenialClassifier.classify_by_message(message, PayerType.MEDICARE)
        assert result.reason == DenialReason.DUPLICATE_CLAIM
        assert result.confidence > 0.0

    def test_classify_by_message_coverage_terminated(self):
        """Test classification for coverage terminated."""
        message = "Patient coverage has been terminated"
        result = DenialClassifier.classify_by_message(message, PayerType.COMMERCIAL)
        assert result.reason == DenialReason.COVERAGE_TERMINATED
        assert result.confidence > 0.0

    def test_classify_by_message_cob_required(self):
        """Test classification for COB required."""
        message = "Coordination of benefits required - patient has other insurance"
        result = DenialClassifier.classify_by_message(message, PayerType.COMMERCIAL)
        assert result.reason == DenialReason.COB_REQUIRED
        assert result.confidence > 0.0

    def test_classify_by_message_timely_filing(self):
        """Test classification for timely filing."""
        message = "Claim submitted after filing deadline"
        result = DenialClassifier.classify_by_message(message, PayerType.MEDICAID)
        assert result.reason == DenialReason.TIMELY_FILING
        assert result.confidence > 0.0

    def test_classify_by_message_unknown(self):
        """Test classification returns UNKNOWN for unrecognized message."""
        message = "Some random denial reason we don't recognize"
        result = DenialClassifier.classify_by_message(message, PayerType.COMMERCIAL)
        assert result.reason == DenialReason.UNKNOWN
        assert result.confidence > 0.0


class TestClassifyDenial:
    """Test full denial classification function."""

    def test_classify_denial_with_code(self):
        """Test classification with known denial code."""
        result = classify_denial(
            payer_type=PayerType.COMMERCIAL,
            denial_code="CO-50",
            denial_message="Invalid CPT code",
        )
        assert result.reason == DenialReason.INVALID_CPT_CODE
        assert result.confidence >= 0.9

    def test_classify_denial_with_message(self):
        """Test classification with denial message."""
        result = classify_denial(
            payer_type=PayerType.MEDICARE,
            denial_code="UNKNOWN-CODE",
            denial_message="Prior authorization required for this service",
        )
        assert result.reason == DenialReason.MISSING_AUTHORIZATION
        assert result.confidence > 0.0

    def test_classify_denial_with_claim_data(self):
        """Test classification uses claim-specific data."""
        result = classify_denial(
            payer_type=PayerType.COMMERCIAL,
            denial_code="UNKNOWN",
            denial_message="Invalid code provided",
            claim_data={
                "cpt_codes": [],  # Empty CPT codes
                "icd_codes": ["E11.9"],
                "amount": 1000.0,
            },
        )
        # Should classify as invalid CPT since CPT codes are empty
        assert result.reason == DenialReason.INVALID_CPT_CODE

    def test_classify_denial_prefers_code_over_message(self):
        """Test that code classification takes precedence when both are provided."""
        result = classify_denial(
            payer_type=PayerType.COMMERCIAL,
            denial_code="CO-19",  # Invalid ICD code
            denial_message="Prior authorization required",  # Would classify as MISSING_AUTHORIZATION
        )
        # Code should take precedence
        assert result.reason == DenialReason.INVALID_ICD_CODE

    def test_classify_denial_unknown_all_inputs(self):
        """Test classification returns UNKNOWN when no patterns match."""
        result = classify_denial(
            payer_type=PayerType.COMMERCIAL,
            denial_code="UNKNOWN-999",
            denial_message="Some completely unrecognized denial reason",
            claim_data={"cpt_codes": ["99213"], "icd_codes": ["E11.9"], "amount": 1000.0},
        )
        assert result.reason == DenialReason.UNKNOWN
        assert result.confidence > 0.0
