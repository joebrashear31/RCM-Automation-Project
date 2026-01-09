"""Unit tests for claim validator."""

import pytest
from datetime import datetime, timedelta
from services.rules.validator import PayerRuleValidator, validate_claim
from services.claims.models import Claim
from common.enums import PayerType, ClaimStatus


class TestPayerRuleValidator:
    """Test payer rule validation logic."""

    def test_validate_cpt_codes_valid(self):
        """Test validation of valid CPT codes."""
        errors, warnings = PayerRuleValidator.validate_cpt_codes(["99213", "36415", "80053"])
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_cpt_codes_empty(self):
        """Test validation fails with empty CPT codes."""
        errors, warnings = PayerRuleValidator.validate_cpt_codes([])
        assert len(errors) > 0
        assert "required" in errors[0].lower()

    def test_validate_cpt_codes_invalid_format(self):
        """Test validation fails with invalid CPT code format."""
        errors, warnings = PayerRuleValidator.validate_cpt_codes(["123", "INVALID", "99213"])
        assert len(errors) >= 2  # "123" and "INVALID" should fail

    def test_validate_cpt_codes_with_modifier(self):
        """Test validation accepts CPT codes with modifiers."""
        errors, warnings = PayerRuleValidator.validate_cpt_codes(["99213", "36415RT"])
        assert len(errors) == 0

    def test_validate_icd_codes_valid(self):
        """Test validation of valid ICD-10 codes."""
        errors, warnings = PayerRuleValidator.validate_icd_codes(["E11.9", "I10", "Z79.4"])
        assert len(errors) == 0

    def test_validate_icd_codes_empty(self):
        """Test validation fails with empty ICD codes."""
        errors, warnings = PayerRuleValidator.validate_icd_codes([])
        assert len(errors) > 0
        assert "required" in errors[0].lower()

    def test_validate_icd_codes_invalid_format(self):
        """Test validation fails with invalid ICD-10 format."""
        errors, warnings = PayerRuleValidator.validate_icd_codes(["INVALID", "E11"])
        assert len(errors) >= 1  # "INVALID" should fail

    def test_validate_provider_npi_valid(self):
        """Test validation of valid NPI."""
        errors, warnings = PayerRuleValidator.validate_provider_npi("1234567890")
        assert len(errors) == 0

    def test_validate_provider_npi_invalid_length(self):
        """Test validation fails with wrong NPI length."""
        errors, warnings = PayerRuleValidator.validate_provider_npi("12345")
        assert len(errors) > 0
        assert "10 digits" in errors[0]

    def test_validate_provider_npi_non_numeric(self):
        """Test validation fails with non-numeric NPI."""
        errors, warnings = PayerRuleValidator.validate_provider_npi("123456789A")
        assert len(errors) > 0

    def test_validate_service_dates_valid(self):
        """Test validation of valid service date range."""
        date_from = datetime(2024, 1, 15)
        date_to = datetime(2024, 1, 15, 23, 59, 59)
        errors, warnings = PayerRuleValidator.validate_service_dates(date_from, date_to)
        assert len(errors) == 0

    def test_validate_service_dates_invalid_range(self):
        """Test validation fails when date_to is before date_from."""
        date_from = datetime(2024, 1, 16)
        date_to = datetime(2024, 1, 15)
        errors, warnings = PayerRuleValidator.validate_service_dates(date_from, date_to)
        assert len(errors) > 0
        assert "date 'to' must be >=" in errors[0].lower()

    def test_validate_service_dates_future_warning(self):
        """Test validation warns about future service dates."""
        future_date = datetime.utcnow() + timedelta(days=30)
        errors, warnings = PayerRuleValidator.validate_service_dates(
            future_date, future_date + timedelta(hours=1)
        )
        assert len(warnings) > 0
        assert "future" in warnings[0].lower()

    def test_validate_medicare_rules(self, db_session):
        """Test Medicare-specific validation rules."""
        claim = Claim(
            claim_number="TEST-001",
            provider_npi="1234567890",
            patient_id="PAT-001",
            payer_id="MEDICARE-001",
            payer_type=PayerType.MEDICARE.value,
            amount=1000.00,
            cpt_codes=["10000"],
            icd_codes=["E11.9"],
            service_date_from=datetime(2024, 1, 15),
            service_date_to=datetime(2024, 1, 15),
            status=ClaimStatus.CREATED.value,
        )

        errors, warnings = PayerRuleValidator.validate_medicare_rules(claim)
        # Should have a warning about CPT starting with "1" needing secondary codes
        assert len(warnings) >= 1
        assert "secondary diagnosis" in warnings[0].lower()

    def test_validate_medicaid_rules_high_value(self, db_session):
        """Test Medicaid validation for high-value claims."""
        claim = Claim(
            claim_number="TEST-002",
            provider_npi="1234567890",
            patient_id="PAT-002",
            payer_id="MEDICAID-001",
            payer_type=PayerType.MEDICAID.value,
            amount=15000.00,  # High value
            cpt_codes=["99213"],
            icd_codes=["E11.9"],
            service_date_from=datetime(2024, 1, 15),
            service_date_to=datetime(2024, 1, 15),
            status=ClaimStatus.CREATED.value,
        )

        errors, warnings = PayerRuleValidator.validate_medicaid_rules(claim)
        assert len(warnings) >= 1
        assert "authorization" in warnings[0].lower()


class TestValidateClaim:
    """Test full claim validation function."""

    def test_validate_claim_valid_commercial(self, db_session):
        """Test validation of a valid commercial claim."""
        claim = Claim(
            claim_number="TEST-001",
            provider_npi="1234567890",
            patient_id="PAT-001",
            payer_id="COMM-001",
            payer_type=PayerType.COMMERCIAL.value,
            amount=1000.00,
            cpt_codes=["99213", "36415"],
            icd_codes=["E11.9", "I10"],
            service_date_from=datetime(2024, 1, 15),
            service_date_to=datetime(2024, 1, 15),
            status=ClaimStatus.CREATED.value,
        )

        result = validate_claim(claim)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_claim_invalid_npi(self, db_session):
        """Test validation fails with invalid NPI."""
        claim = Claim(
            claim_number="TEST-002",
            provider_npi="12345",  # Invalid NPI
            patient_id="PAT-002",
            payer_id="COMM-002",
            payer_type=PayerType.COMMERCIAL.value,
            amount=1000.00,
            cpt_codes=["99213"],
            icd_codes=["E11.9"],
            service_date_from=datetime(2024, 1, 15),
            service_date_to=datetime(2024, 1, 15),
            status=ClaimStatus.CREATED.value,
        )

        result = validate_claim(claim)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_claim_invalid_cpt_code(self, db_session):
        """Test validation fails with invalid CPT code."""
        claim = Claim(
            claim_number="TEST-003",
            provider_npi="1234567890",
            patient_id="PAT-003",
            payer_id="COMM-003",
            payer_type=PayerType.COMMERCIAL.value,
            amount=1000.00,
            cpt_codes=["INVALID"],  # Invalid CPT
            icd_codes=["E11.9"],
            service_date_from=datetime(2024, 1, 15),
            service_date_to=datetime(2024, 1, 15),
            status=ClaimStatus.CREATED.value,
        )

        result = validate_claim(claim)
        assert result.is_valid is False
        assert any("cpt" in error.lower() for error in result.errors)

    def test_validate_claim_multiple_errors(self, db_session):
        """Test validation returns multiple errors."""
        claim = Claim(
            claim_number="TEST-004",
            provider_npi="123",  # Invalid NPI
            patient_id="PAT-004",
            payer_id="COMM-004",
            payer_type=PayerType.COMMERCIAL.value,
            amount=1000.00,
            cpt_codes=["INVALID"],  # Invalid CPT
            icd_codes=["BAD"],  # Invalid ICD
            service_date_from=datetime(2024, 1, 16),
            service_date_to=datetime(2024, 1, 15),  # Invalid date range
            status=ClaimStatus.CREATED.value,
        )

        result = validate_claim(claim)
        assert result.is_valid is False
        assert len(result.errors) >= 3  # NPI, CPT, ICD, and date errors
