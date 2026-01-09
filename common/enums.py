"""Enumerations for RCM workflow states and types."""

from enum import Enum

# all the claim statuses
class ClaimStatus(str, Enum):
    """Claim lifecycle states."""

    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"  # Pre-adjudication rejection
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"  # Post-adjudication denial
    APPEAL_PENDING = "APPEAL_PENDING"
    RESUBMITTED = "RESUBMITTED"
    PAID = "PAID"
    WRITE_OFF = "WRITE_OFF"

# denial reaons
class DenialReason(str, Enum):
    """Common denial reasons."""

    INVALID_CPT_CODE = "INVALID_CPT_CODE"
    INVALID_ICD_CODE = "INVALID_ICD_CODE"
    MISSING_AUTHORIZATION = "MISSING_AUTHORIZATION"
    DUPLICATE_CLAIM = "DUPLICATE_CLAIM"
    COVERAGE_TERMINATED = "COVERAGE_TERMINATED"
    COB_REQUIRED = "COB_REQUIRED"  # Coordination of Benefits
    TIMELY_FILING = "TIMELY_FILING"
    INVALID_PROVIDER = "INVALID_PROVIDER"
    UNKNOWN = "UNKNOWN"


class PayerType(str, Enum):
    """Payer categories."""

    COMMERCIAL = "COMMERCIAL"
    MEDICARE = "MEDICARE"
    MEDICAID = "MEDICAID"
    SELF_PAY = "SELF_PAY"


class ValidationSeverity(str, Enum):
    """Validation rule severity levels."""

    ERROR = "ERROR"  # Blocks state transition
    WARNING = "WARNING"  # Allows transition but flags issue
    INFO = "INFO"  # Informational only


class DenialCategory(str, Enum):
    """Normalized denial categories for agent reasoning."""

    ELIGIBILITY = "ELIGIBILITY"  # Coverage terminated, COB required, etc.
    MEDICAL_NECESSITY = "MEDICAL_NECESSITY"  # Not medically necessary
    CODING_ERROR = "CODING_ERROR"  # Invalid CPT/ICD codes
    PRIOR_AUTH_MISSING = "PRIOR_AUTH_MISSING"  # Missing authorization
    TIMELY_FILING = "TIMELY_FILING"  # Filed too late
    COVERAGE_EXHAUSTED = "COVERAGE_EXHAUSTED"  # Benefits exhausted
    DUPLICATE = "DUPLICATE"  # Duplicate claim
    DOCUMENTATION = "DOCUMENTATION"  # Missing documentation
    UNKNOWN = "UNKNOWN"  # Unclassified


class RecommendedAction(str, Enum):
    """Recommended actions for denial resolution."""

    RESUBMIT = "RESUBMIT"  # Fix and resubmit
    APPEAL = "APPEAL"  # File appeal
    WRITE_OFF = "WRITE_OFF"  # Write off as uncollectible
    REQUEST_AUTH = "REQUEST_AUTH"  # Request prior authorization
    COLLECT_PATIENT = "COLLECT_PATIENT"  # Bill patient directly
    NO_ACTION = "NO_ACTION"  # No action needed or pending review


class AgentDecision(str, Enum):
    """Agent decision outcomes."""

    RESUBMIT = "RESUBMIT"
    APPEAL = "APPEAL"
    WRITE_OFF = "WRITE_OFF"
    REQUEST_AUTH = "REQUEST_AUTH"
    COLLECT_PATIENT = "COLLECT_PATIENT"
    FLAG_FOR_HUMAN = "FLAG_FOR_HUMAN"  # Low confidence, needs review
    NO_ACTION = "NO_ACTION"


class EventType(str, Enum):
    """Types of events in the event log."""

    CLAIM_CREATED = "CLAIM_CREATED"
    CLAIM_VALIDATED = "CLAIM_VALIDATED"
    CLAIM_SUBMITTED = "CLAIM_SUBMITTED"
    CLAIM_REJECTED = "CLAIM_REJECTED"
    CLAIM_ACCEPTED = "CLAIM_ACCEPTED"
    CLAIM_DENIED = "CLAIM_DENIED"
    DENIAL_CLASSIFIED = "DENIAL_CLASSIFIED"
    APPEAL_FILED = "APPEAL_FILED"
    CLAIM_RESUBMITTED = "CLAIM_RESUBMITTED"
    CLAIM_PAID = "CLAIM_PAID"
    CLAIM_WRITTEN_OFF = "CLAIM_WRITTEN_OFF"
    AGENT_DECISION = "AGENT_DECISION"
    HUMAN_OVERRIDE = "HUMAN_OVERRIDE"
    WORKFLOW_EXECUTED = "WORKFLOW_EXECUTED"

