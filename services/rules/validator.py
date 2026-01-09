"""Payer rule validation engine."""

from typing import List, NamedTuple
from services.claims.models import Claim
from common.enums import ValidationSeverity
import re
import logging

logger = logging.getLogger(__name__)


class ValidationResult(NamedTuple):
    """Result of claim validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]


class PayerRuleValidator:
    """Validates claims against payer-specific rules."""

    # CPT code format: 5 digits, optionally followed by 2-character modifier
    CPT_CODE_PATTERN = re.compile(r"^\d{5}([A-Z]{2})?$")

    # ICD-10 code format: Letter followed by 3-7 alphanumeric characters
    ICD10_CODE_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{0,4})?$")

    @classmethod
    def validate_cpt_codes(cls, cpt_codes: List[str]) -> tuple[List[str], List[str]]:
        """Validate CPT code format."""
        errors = []
        warnings = []

        if not cpt_codes:
            errors.append("At least one CPT code is required")

        for code in cpt_codes:
            if not cls.CPT_CODE_PATTERN.match(code):
                errors.append(f"Invalid CPT code format: {code}")

        return errors, warnings

    @classmethod
    def validate_icd_codes(cls, icd_codes: List[str]) -> tuple[List[str], List[str]]:
        """Validate ICD-10 code format."""
        errors = []
        warnings = []

        if not icd_codes:
            errors.append("At least one ICD code is required")

        for code in icd_codes:
            if not cls.ICD10_CODE_PATTERN.match(code):
                errors.append(f"Invalid ICD-10 code format: {code}")

        return errors, warnings

    @classmethod
    def validate_provider_npi(cls, npi: str) -> tuple[List[str], List[str]]:
        """Validate NPI format (10 digits)."""
        errors = []
        warnings = []

        if not npi.isdigit() or len(npi) != 10:
            errors.append(f"Invalid NPI format: {npi} (must be 10 digits)")

        return errors, warnings

    @classmethod
    def validate_service_dates(cls, date_from, date_to) -> tuple[List[str], List[str]]:
        """Validate service date range."""
        errors = []
        warnings = []

        if date_to < date_from:
            errors.append("Service date 'to' must be >= service date 'from'")

        # Check for future dates (warning, not error)
        from datetime import datetime
        if date_from > datetime.utcnow():
            warnings.append("Service date is in the future")

        return errors, warnings

    @classmethod
    def validate_medicare_rules(cls, claim: Claim) -> tuple[List[str], List[str]]:
        """Medicare-specific validation rules."""
        errors = []
        warnings = []

        # Medicare requires both primary ICD and often secondary codes
        if len(claim.icd_codes) < 1:
            errors.append("Medicare requires at least one ICD-10 code")

        # Medicare has specific CPT coverage rules (simplified)
        for cpt in claim.cpt_codes:
            # Example: Medicare doesn't cover some cosmetic procedures
            if cpt.startswith("1") and len(claim.icd_codes) < 2:
                warnings.append(
                    f"CPT {cpt} may require secondary diagnosis codes for Medicare"
                )

        return errors, warnings

    @classmethod
    def validate_medicaid_rules(cls, claim: Claim) -> tuple[List[str], List[str]]:
        """Medicaid-specific validation rules."""
        errors = []
        warnings = []

        # Medicaid often requires more detailed documentation
        if claim.amount > 10000:
            warnings.append("High-value claim may require prior authorization for Medicaid")

        return errors, warnings

    @classmethod
    def validate_commercial_rules(cls, claim: Claim) -> tuple[List[str], List[str]]:
        """Commercial payer validation rules."""
        errors = []
        warnings = []

        # Commercial payers may have different requirements
        # This is a simplified example
        return errors, warnings


def validate_claim(claim: Claim) -> ValidationResult:
    """
    Validate a claim against payer rules.

    Returns ValidationResult with errors, warnings, and info messages.
    """
    all_errors = []
    all_warnings = []
    all_info = []

    # Universal validations
    cpt_errors, cpt_warnings = PayerRuleValidator.validate_cpt_codes(claim.cpt_codes)
    all_errors.extend(cpt_errors)
    all_warnings.extend(cpt_warnings)

    icd_errors, icd_warnings = PayerRuleValidator.validate_icd_codes(claim.icd_codes)
    all_errors.extend(icd_errors)
    all_warnings.extend(icd_warnings)

    npi_errors, npi_warnings = PayerRuleValidator.validate_provider_npi(claim.provider_npi)
    all_errors.extend(npi_errors)
    all_warnings.extend(npi_warnings)

    date_errors, date_warnings = PayerRuleValidator.validate_service_dates(
        claim.service_date_from, claim.service_date_to
    )
    all_errors.extend(date_errors)
    all_warnings.extend(date_warnings)

    # Payer-specific validations
    payer_type = claim.payer_type.upper()
    if payer_type == "MEDICARE":
        medicare_errors, medicare_warnings = PayerRuleValidator.validate_medicare_rules(claim)
        all_errors.extend(medicare_errors)
        all_warnings.extend(medicare_warnings)
    elif payer_type == "MEDICAID":
        medicaid_errors, medicaid_warnings = PayerRuleValidator.validate_medicaid_rules(claim)
        all_errors.extend(medicaid_errors)
        all_warnings.extend(medicaid_warnings)
    elif payer_type == "COMMERCIAL":
        commercial_errors, commercial_warnings = PayerRuleValidator.validate_commercial_rules(claim)
        all_errors.extend(commercial_errors)
        all_warnings.extend(commercial_warnings)

    is_valid = len(all_errors) == 0

    return ValidationResult(
        is_valid=is_valid, errors=all_errors, warnings=all_warnings, info=all_info
    )

