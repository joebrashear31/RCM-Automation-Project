"""Denial reason classification engine."""

from typing import Dict, NamedTuple, Optional
from common.enums import DenialReason, PayerType, DenialCategory, RecommendedAction
import re
import logging

logger = logging.getLogger(__name__)


class DenialClassification(NamedTuple):
    """Classification result for a denial."""

    reason: DenialReason
    category: DenialCategory  # Normalized category for agent reasoning
    confidence: float  # 0.0 to 1.0
    details: str


class DenialClassifier:
    """Classifies denial reasons from payer codes and messages."""

    # Map DenialReason to normalized DenialCategory
    REASON_TO_CATEGORY = {
        DenialReason.COVERAGE_TERMINATED: DenialCategory.ELIGIBILITY,
        DenialReason.COB_REQUIRED: DenialCategory.ELIGIBILITY,
        DenialReason.INVALID_PROVIDER: DenialCategory.ELIGIBILITY,
        DenialReason.INVALID_CPT_CODE: DenialCategory.CODING_ERROR,
        DenialReason.INVALID_ICD_CODE: DenialCategory.CODING_ERROR,
        DenialReason.MISSING_AUTHORIZATION: DenialCategory.PRIOR_AUTH_MISSING,
        DenialReason.TIMELY_FILING: DenialCategory.TIMELY_FILING,
        DenialReason.DUPLICATE_CLAIM: DenialCategory.DUPLICATE,
        DenialReason.UNKNOWN: DenialCategory.UNKNOWN,
    }

    # Common denial code patterns
    DENIAL_PATTERNS = {
        DenialReason.INVALID_CPT_CODE: [
            r"invalid.*cpt",
            r"cpt.*not.*covered",
            r"procedure.*code.*invalid",
            r"CO-50",  # Common denial code
        ],
        DenialReason.INVALID_ICD_CODE: [
            r"invalid.*diagnosis",
            r"icd.*not.*valid",
            r"diagnosis.*code.*invalid",
            r"CO-19",
        ],
        DenialReason.MISSING_AUTHORIZATION: [
            r"authorization.*required",
            r"prior.*auth.*required",
            r"pre.*authorization",
            r"CO-29",
        ],
        DenialReason.DUPLICATE_CLAIM: [
            r"duplicate",
            r"already.*processed",
            r"previously.*paid",
            r"CO-18",
        ],
        DenialReason.COVERAGE_TERMINATED: [
            r"coverage.*terminated",
            r"coverage.*ended",
            r"benefits.*exhausted",
            r"CO-11",
        ],
        DenialReason.COB_REQUIRED: [
            r"coordination.*benefits",
            r"cob.*required",
            r"other.*insurance",
            r"CO-197",
        ],
        DenialReason.TIMELY_FILING: [
            r"timely.*filing",
            r"filing.*deadline",
            r"submitted.*late",
            r"CO-29",
        ],
        DenialReason.INVALID_PROVIDER: [
            r"provider.*not.*eligible",
            r"invalid.*provider",
            r"provider.*number.*invalid",
        ],
    }

    @classmethod
    def classify_by_message(cls, denial_message: str, payer_type: PayerType) -> DenialClassification:
        """
        Classify denial reason from payer message text.

        Uses pattern matching to identify common denial reasons.
        """
        denial_message_lower = denial_message.lower()
        best_match = None
        best_confidence = 0.0

        for reason, patterns in cls.DENIAL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, denial_message_lower, re.IGNORECASE):
                    # Simple confidence scoring: exact match = 1.0, partial = 0.7
                    confidence = 1.0 if pattern.lower() in denial_message_lower else 0.7
                    if confidence > best_confidence:
                        best_match = reason
                        best_confidence = confidence

        if best_match:
            category = DenialClassifier.REASON_TO_CATEGORY.get(best_match, DenialCategory.UNKNOWN)
            return DenialClassification(
                reason=best_match,
                category=category,
                confidence=best_confidence,
                details=f"Classified from message: {denial_message[:200]}",
            )

        # Default to UNKNOWN if no pattern matches
        return DenialClassification(
            reason=DenialReason.UNKNOWN,
            category=DenialCategory.UNKNOWN,
            confidence=0.5,
            details=f"Unable to classify denial message: {denial_message[:200]}",
        )

    @classmethod
    def classify_by_code(
        cls, denial_code: str, payer_type: PayerType
    ) -> DenialClassification:
        """
        Classify denial reason from payer denial code.

        Maps common denial codes (e.g., CO-50, CO-29) to reasons.
        """
        code_upper = denial_code.upper()

        # Map common denial codes
        code_mapping = {
            "CO-50": DenialReason.INVALID_CPT_CODE,
            "CO-19": DenialReason.INVALID_ICD_CODE,
            "CO-29": DenialReason.MISSING_AUTHORIZATION,
            "CO-18": DenialReason.DUPLICATE_CLAIM,
            "CO-11": DenialReason.COVERAGE_TERMINATED,
            "CO-197": DenialReason.COB_REQUIRED,
            "CO-16": DenialReason.TIMELY_FILING,
        }

        if code_upper in code_mapping:
            reason = code_mapping[code_upper]
            category = DenialClassifier.REASON_TO_CATEGORY.get(reason, DenialCategory.UNKNOWN)
            return DenialClassification(
                reason=reason,
                category=category,
                confidence=0.9,
                details=f"Classified from denial code: {denial_code}",
            )

        return DenialClassification(
            reason=DenialReason.UNKNOWN,
            category=DenialCategory.UNKNOWN,
            confidence=0.3,
            details=f"Unknown denial code: {denial_code}",
        )

    @classmethod
    def classify_claim_specific(
        cls, denial_code: str, denial_message: str, claim_data: Dict
    ) -> Optional[DenialReason]:
        """
        Use claim-specific data to refine classification.

        Example: If claim has unusual CPT/ICD combinations, might indicate invalid codes.
        """
        # Example logic: check if CPT codes seem invalid based on patterns
        cpt_codes = claim_data.get("cpt_codes", [])
        icd_codes = claim_data.get("icd_codes", [])

        # If denial mentions codes and we have unusual combinations, might be invalid codes
        if "code" in denial_message.lower():
            if len(cpt_codes) == 0 or len(icd_codes) == 0:
                return DenialReason.INVALID_CPT_CODE if len(cpt_codes) == 0 else DenialReason.INVALID_ICD_CODE

        return None


def classify_denial(
    payer_type: PayerType,
    denial_code: str,
    denial_message: str,
    claim_data: Optional[Dict] = None,
) -> DenialClassification:
    """
    Classify a denial reason from payer information.

    Combines multiple classification strategies for best accuracy.
    """
    if claim_data is None:
        claim_data = {}

    classifications = []

    # Classify by code (high confidence if known code)
    code_classification = DenialClassifier.classify_by_code(denial_code, payer_type)
    classifications.append(code_classification)

    # Classify by message
    message_classification = DenialClassifier.classify_by_message(denial_message, payer_type)
    classifications.append(message_classification)

    # Use claim-specific data if available
    claim_specific_reason = DenialClassifier.classify_claim_specific(
        denial_code, denial_message, claim_data
    )
    if claim_specific_reason:
        category = DenialClassifier.REASON_TO_CATEGORY.get(claim_specific_reason, DenialCategory.UNKNOWN)
        classifications.append(
            DenialClassification(
                reason=claim_specific_reason,
                category=category,
                confidence=0.6,
                details="Classified from claim data"
            )
        )

    # Combine classifications: prefer higher confidence, prefer non-UNKNOWN
    non_unknown = [c for c in classifications if c.reason != DenialReason.UNKNOWN]
    if non_unknown:
        # Return highest confidence non-UNKNOWN classification
        best = max(non_unknown, key=lambda c: c.confidence)
        return best

    # If all are UNKNOWN, return the highest confidence one
    return max(classifications, key=lambda c: c.confidence)


def get_recommended_action(denial_category: DenialCategory) -> RecommendedAction:
    """
    Get rule-based recommended action for a denial category.
    
    This is the deterministic baseline that agents can override.
    
    Rules:
    - ELIGIBILITY → WRITE_OFF (usually can't fix eligibility issues)
    - CODING_ERROR → RESUBMIT (fix codes and resubmit)
    - MEDICAL_NECESSITY → APPEAL (requires clinical documentation)
    - PRIOR_AUTH_MISSING → REQUEST_AUTH (obtain authorization)
    - TIMELY_FILING → WRITE_OFF (can't fix late filing)
    - COVERAGE_EXHAUSTED → WRITE_OFF or COLLECT_PATIENT
    - DUPLICATE → NO_ACTION or investigate
    """
    action_mapping = {
        DenialCategory.ELIGIBILITY: RecommendedAction.WRITE_OFF,
        DenialCategory.CODING_ERROR: RecommendedAction.RESUBMIT,
        DenialCategory.MEDICAL_NECESSITY: RecommendedAction.APPEAL,
        DenialCategory.PRIOR_AUTH_MISSING: RecommendedAction.REQUEST_AUTH,
        DenialCategory.TIMELY_FILING: RecommendedAction.WRITE_OFF,
        DenialCategory.COVERAGE_EXHAUSTED: RecommendedAction.WRITE_OFF,
        DenialCategory.DUPLICATE: RecommendedAction.NO_ACTION,
        DenialCategory.DOCUMENTATION: RecommendedAction.APPEAL,
        DenialCategory.UNKNOWN: RecommendedAction.NO_ACTION,
    }
    
    return action_mapping.get(denial_category, RecommendedAction.NO_ACTION)

