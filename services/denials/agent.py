"""Denial Resolution Agent - Stateless decision-maker for denial handling.

This agent does NOT execute actions. It only makes decisions that the backend executes.
All decisions are logged for auditability and explainability.
"""

from typing import Dict, List, NamedTuple, Optional
from decimal import Decimal
from common.enums import (
    DenialCategory,
    RecommendedAction,
    AgentDecision as AgentDecisionEnum,
    PayerType,
)
import logging

logger = logging.getLogger(__name__)


class AgentDecisionResult(NamedTuple):
    """Result of agent decision-making."""

    decision: AgentDecisionEnum
    confidence: float  # 0.0 to 1.0
    rationale: str
    missing_info: List[str]
    rule_based_recommendation: RecommendedAction


class DenialResolutionAgent:
    """Agentic AI decision-maker for denial resolution.
    
    This agent:
    - Takes claim data, denial info, and historical context
    - Makes decisions (not executes them)
    - Is stateless (no DB writes)
    - Returns structured decisions with rationale
    
    All decisions are logged by the caller for auditability.
    """

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.8
    LOW_CONFIDENCE_THRESHOLD = 0.6

    @classmethod
    def make_decision(
        cls,
        claim_data: Dict,
        denial_category: DenialCategory,
        payer_type: PayerType,
        rule_based_recommendation: RecommendedAction,
        historical_success_rate: Optional[float] = None,
        payer_history: Optional[Dict] = None,
    ) -> AgentDecisionResult:
        """
        Make a decision on how to handle a denial.
        
        Args:
            claim_data: Claim information (amount, codes, dates, etc.)
            denial_category: Normalized denial category
            payer_type: Type of payer
            rule_based_recommendation: Deterministic rule recommendation
            historical_success_rate: Success rate for this action/category combination
            payer_history: Historical data about this payer
            
        Returns:
            AgentDecisionResult with decision, confidence, and rationale
        """
        missing_info = cls._identify_missing_info(claim_data, denial_category)
        
        # Build context for decision-making
        context = {
            "denial_category": denial_category,
            "payer_type": payer_type,
            "claim_amount": claim_data.get("amount", 0),
            "historical_success_rate": historical_success_rate,
            "rule_based_recommendation": rule_based_recommendation,
        }
        
        # Agent reasoning logic
        decision, confidence, rationale = cls._reason_about_denial(context, missing_info)
        
        # If confidence is low, flag for human review
        if confidence < cls.LOW_CONFIDENCE_THRESHOLD:
            decision = AgentDecisionEnum.FLAG_FOR_HUMAN
            rationale += f" Low confidence ({confidence:.2f}) requires human review."
        
        return AgentDecisionResult(
            decision=decision,
            confidence=confidence,
            rationale=rationale,
            missing_info=missing_info,
            rule_based_recommendation=rule_based_recommendation,
        )

    @classmethod
    def _identify_missing_info(cls, claim_data: Dict, denial_category: DenialCategory) -> List[str]:
        """Identify missing information that would improve decision quality."""
        missing = []
        
        if denial_category == DenialCategory.PRIOR_AUTH_MISSING:
            if not claim_data.get("authorization_number"):
                missing.append("prior_authorization_number")
        
        if denial_category == DenialCategory.MEDICAL_NECESSITY:
            if not claim_data.get("clinical_notes"):
                missing.append("clinical_documentation")
        
        if denial_category == DenialCategory.CODING_ERROR:
            if not claim_data.get("coding_review_performed"):
                missing.append("coding_audit")
        
        # Always check for appeal history if considering appeal
        if not claim_data.get("previous_appeal_attempts"):
            missing.append("appeal_history")
        
        return missing

    @classmethod
    def _reason_about_denial(
        cls, context: Dict, missing_info: List[str]
    ) -> tuple[AgentDecisionEnum, float, str]:
        """
        Core reasoning logic for denial resolution.
        
        This is where the "agent" logic lives. In production, this could:
        - Call an LLM with structured prompts
        - Use a fine-tuned model
        - Use rule-based logic enhanced with ML
        
        For now, we use rule-based logic with confidence scoring.
        """
        denial_category = context["denial_category"]
        rule_recommendation = context["rule_based_recommendation"]
        historical_success_rate = context.get("historical_success_rate")
        claim_amount = context.get("claim_amount", 0)
        
        # Start with rule-based recommendation
        base_confidence = 0.7
        rationale = f"Rule-based recommendation: {rule_recommendation.value} for {denial_category.value} denial."
        
        # Adjust based on historical success
        if historical_success_rate is not None:
            if historical_success_rate > 0.7:
                base_confidence += 0.15
                rationale += f" High historical success rate ({historical_success_rate:.0%})."
            elif historical_success_rate < 0.3:
                base_confidence -= 0.2
                rationale += f" Low historical success rate ({historical_success_rate:.0%}), considering alternatives."
        
        # Adjust based on claim amount (higher value = more scrutiny)
        if claim_amount > 10000:
            rationale += f" High-value claim (${claim_amount:,.2f}), recommend careful review."
            if rule_recommendation == RecommendedAction.WRITE_OFF:
                # Be more cautious about writing off high-value claims
                base_confidence -= 0.1
        
        # Adjust based on missing information
        if missing_info:
            base_confidence -= 0.1 * min(len(missing_info), 3)
            rationale += f" Missing information: {', '.join(missing_info)}."
        
        # Category-specific logic
        if denial_category == DenialCategory.ELIGIBILITY:
            # Eligibility issues are usually hard to fix
            decision = AgentDecisionEnum.WRITE_OFF
            if historical_success_rate and historical_success_rate > 0.5:
                # If we've had success with appeals on eligibility, try appeal
                decision = AgentDecisionEnum.APPEAL
                rationale += " Historical data suggests appeal may be successful."
            
        elif denial_category == DenialCategory.CODING_ERROR:
            # Coding errors are usually fixable
            decision = AgentDecisionEnum.RESUBMIT
            rationale += " Coding errors can typically be corrected and resubmitted."
            
        elif denial_category == DenialCategory.MEDICAL_NECESSITY:
            # Medical necessity requires clinical documentation
            if missing_info and "clinical_documentation" in missing_info:
                decision = AgentDecisionEnum.FLAG_FOR_HUMAN
                rationale += " Missing clinical documentation required for appeal."
            else:
                decision = AgentDecisionEnum.APPEAL
                rationale += " Medical necessity denials often succeed on appeal with proper documentation."
                
        elif denial_category == DenialCategory.PRIOR_AUTH_MISSING:
            # Try to get authorization first
            decision = AgentDecisionEnum.REQUEST_AUTH
            rationale += " Attempt to obtain prior authorization, then resubmit."
            
        elif denial_category == DenialCategory.TIMELY_FILING:
            # Late filing is usually not fixable
            decision = AgentDecisionEnum.WRITE_OFF
            rationale += " Timely filing denials cannot typically be resolved."
            
        elif denial_category == DenialCategory.COVERAGE_EXHAUSTED:
            # May be able to bill patient
            if claim_amount < 5000:
                decision = AgentDecisionEnum.WRITE_OFF
            else:
                decision = AgentDecisionEnum.COLLECT_PATIENT
            rationale += " Coverage exhausted - consider patient responsibility."
            
        elif denial_category == DenialCategory.DUPLICATE:
            # Investigate first
            decision = AgentDecisionEnum.FLAG_FOR_HUMAN
            rationale += " Duplicate claim requires investigation before action."
            
        else:
            # Unknown or edge cases
            decision = AgentDecisionEnum.FLAG_FOR_HUMAN
            base_confidence = 0.5
            rationale += " Unclear category, requires human review."
        
        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, base_confidence))
        
        return decision, confidence, rationale


def make_agent_decision(
    claim_data: Dict,
    denial_category: DenialCategory,
    payer_type: PayerType,
    rule_based_recommendation: RecommendedAction,
    historical_success_rate: Optional[float] = None,
    payer_history: Optional[Dict] = None,
) -> AgentDecisionResult:
    """
    Public interface for making agent decisions.
    
    This is the stateless entry point - it does NOT write to database.
    Caller is responsible for logging the decision.
    """
    return DenialResolutionAgent.make_decision(
        claim_data=claim_data,
        denial_category=denial_category,
        payer_type=payer_type,
        rule_based_recommendation=rule_based_recommendation,
        historical_success_rate=historical_success_rate,
        payer_history=payer_history,
    )
