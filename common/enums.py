"""Enumerations for RCM workflow states and types."""

from enum import Enum


class ClaimStatus(str, Enum):
    """Claim lifecycle states."""

    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"
    PAID = "PAID"
    RESUBMITTED = "RESUBMITTED"


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

