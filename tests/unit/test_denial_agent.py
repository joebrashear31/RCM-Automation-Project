"""Unit tests for denial resolution agent."""

import pytest
from services.denials.agent import DenialResolutionAgent, make_agent_decision
from common.enums import (
    DenialCategory,
    RecommendedAction,
    AgentDecision as AgentDecisionEnum,
    PayerType,
)


class TestDenialResolutionAgent:
    """Test denial resolution agent logic."""

    def test_make_decision_coding_error(self):
        """Test agent decision for coding error denial."""
        claim_data = {
            "amount": 1000.0,
            "cpt_codes": ["99213"],
            "icd_codes": ["E11.9"],
        }

        result = make_agent_decision(
            claim_data=claim_data,
            denial_category=DenialCategory.CODING_ERROR,
            payer_type=PayerType.COMMERCIAL,
            rule_based_recommendation=RecommendedAction.RESUBMIT,
        )

        assert result.decision == AgentDecisionEnum.RESUBMIT
        assert result.confidence > 0.5
        assert "coding" in result.rationale.lower() or "resubmit" in result.rationale.lower()
        assert result.rule_based_recommendation == RecommendedAction.RESUBMIT

    def test_make_decision_eligibility(self):
        """Test agent decision for eligibility denial."""
        claim_data = {
            "amount": 500.0,
            "cpt_codes": ["99213"],
        }

        result = make_agent_decision(
            claim_data=claim_data,
            denial_category=DenialCategory.ELIGIBILITY,
            payer_type=PayerType.COMMERCIAL,
            rule_based_recommendation=RecommendedAction.WRITE_OFF,
        )

        # Eligibility usually results in write-off
        assert result.decision in [AgentDecisionEnum.WRITE_OFF, AgentDecisionEnum.APPEAL]
        assert result.confidence > 0.0
        assert result.rule_based_recommendation == RecommendedAction.WRITE_OFF

    def test_make_decision_medical_necessity(self):
        """Test agent decision for medical necessity denial."""
        claim_data = {
            "amount": 2000.0,
            "cpt_codes": ["99213"],
            "clinical_notes": "Patient requires treatment",  # Has documentation
        }

        result = make_agent_decision(
            claim_data=claim_data,
            denial_category=DenialCategory.MEDICAL_NECESSITY,
            payer_type=PayerType.COMMERCIAL,
            rule_based_recommendation=RecommendedAction.APPEAL,
        )

        assert result.decision == AgentDecisionEnum.APPEAL
        assert "medical necessity" in result.rationale.lower() or "appeal" in result.rationale.lower()

    def test_make_decision_medical_necessity_missing_docs(self):
        """Test agent flags medical necessity when docs are missing."""
        claim_data = {
            "amount": 2000.0,
            "cpt_codes": ["99213"],
            # No clinical_notes
        }

        result = make_agent_decision(
            claim_data=claim_data,
            denial_category=DenialCategory.MEDICAL_NECESSITY,
            payer_type=PayerType.COMMERCIAL,
            rule_based_recommendation=RecommendedAction.APPEAL,
        )

        # Should flag for human review if missing docs
        assert "clinical" in " ".join(result.missing_info).lower() or result.decision == AgentDecisionEnum.FLAG_FOR_HUMAN

    def test_make_decision_prior_auth(self):
        """Test agent decision for missing prior auth."""
        claim_data = {
            "amount": 1500.0,
        }

        result = make_agent_decision(
            claim_data=claim_data,
            denial_category=DenialCategory.PRIOR_AUTH_MISSING,
            payer_type=PayerType.COMMERCIAL,
            rule_based_recommendation=RecommendedAction.REQUEST_AUTH,
        )

        assert result.decision == AgentDecisionEnum.REQUEST_AUTH
        assert "authorization" in result.rationale.lower()

    def test_make_decision_high_value_claim(self):
        """Test agent is more cautious with high-value claims."""
        claim_data = {
            "amount": 50000.0,  # High value
            "cpt_codes": ["99213"],
        }

        result = make_agent_decision(
            claim_data=claim_data,
            denial_category=DenialCategory.ELIGIBILITY,
            payer_type=PayerType.COMMERCIAL,
            rule_based_recommendation=RecommendedAction.WRITE_OFF,
        )

        assert "high-value" in result.rationale.lower() or "$" in result.rationale
        # Should be more cautious (lower confidence or flag for review)
        assert result.confidence < 0.9 or result.decision == AgentDecisionEnum.FLAG_FOR_HUMAN

    def test_make_decision_with_historical_success(self):
        """Test agent adjusts confidence based on historical success."""
        claim_data = {
            "amount": 1000.0,
        }

        result = make_agent_decision(
            claim_data=claim_data,
            denial_category=DenialCategory.CODING_ERROR,
            payer_type=PayerType.COMMERCIAL,
            rule_based_recommendation=RecommendedAction.RESUBMIT,
            historical_success_rate=0.85,  # High success rate
        )

        assert result.confidence >= 0.7
        assert "historical" in result.rationale.lower() or "success" in result.rationale.lower()

    def test_make_decision_low_confidence_flags_for_human(self):
        """Test that low confidence decisions are flagged."""
        claim_data = {
            "amount": 1000.0,
        }

        result = make_agent_decision(
            claim_data=claim_data,
            denial_category=DenialCategory.UNKNOWN,  # Unknown category
            payer_type=PayerType.COMMERCIAL,
            rule_based_recommendation=RecommendedAction.NO_ACTION,
        )

        # Low confidence should flag for human
        assert result.confidence < DenialResolutionAgent.LOW_CONFIDENCE_THRESHOLD
        assert result.decision == AgentDecisionEnum.FLAG_FOR_HUMAN

    def test_identify_missing_info(self):
        """Test agent identifies missing information."""
        claim_data = {
            "amount": 1000.0,
            # Missing authorization_number for PRIOR_AUTH_MISSING
        }

        result = make_agent_decision(
            claim_data=claim_data,
            denial_category=DenialCategory.PRIOR_AUTH_MISSING,
            payer_type=PayerType.COMMERCIAL,
            rule_based_recommendation=RecommendedAction.REQUEST_AUTH,
        )

        assert len(result.missing_info) > 0
        assert any("auth" in info.lower() for info in result.missing_info)
