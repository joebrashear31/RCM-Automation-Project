"""Integration tests for API routes."""

import pytest
from fastapi import status
from common.enums import ClaimStatus, PayerType
from services.claims.models import Claim, ClaimStateTransition


class TestClaimRoutes:
    """Test claim API endpoints."""

    def test_create_claim(self, client, sample_claim_data):
        """Test creating a new claim."""
        response = client.post("/claims/", json=sample_claim_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["claim_number"] == sample_claim_data["claim_number"]
        assert data["status"] == ClaimStatus.CREATED.value
        assert data["provider_npi"] == sample_claim_data["provider_npi"]
        assert "id" in data

    def test_create_claim_duplicate_claim_number(self, client, sample_claim_data):
        """Test creating a claim with duplicate claim number fails."""
        # Create first claim
        response = client.post("/claims/", json=sample_claim_data)
        assert response.status_code == status.HTTP_201_CREATED

        # Try to create duplicate
        response = client.post("/claims/", json=sample_claim_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()

    def test_get_claim(self, client, sample_claim):
        """Test retrieving a single claim."""
        response = client.get(f"/claims/{sample_claim.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_claim.id
        assert data["claim_number"] == sample_claim.claim_number

    def test_get_claim_not_found(self, client):
        """Test retrieving a non-existent claim returns 404."""
        response = client.get("/claims/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_claims(self, client, db_session, sample_claim_data):
        """Test listing claims."""
        # Create multiple claims
        for i in range(3):
            claim_data = sample_claim_data.copy()
            claim_data["claim_number"] = f"CLM-{i:03d}"
            client.post("/claims/", json=claim_data)

        response = client.get("/claims/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 3

    def test_list_claims_with_status_filter(self, client, db_session, sample_claim):
        """Test listing claims filtered by status."""
        # Create a validated claim
        claim_data = {
            "claim_number": "CLM-VALIDATED",
            "provider_npi": "1234567890",
            "patient_id": "PAT-001",
            "payer_id": "PAY-001",
            "payer_type": PayerType.COMMERCIAL.value,
            "amount": 1000.0,
            "cpt_codes": ["99213"],
            "icd_codes": ["E11.9"],
            "service_date_from": "2024-01-15T10:00:00",
            "service_date_to": "2024-01-15T10:30:00",
        }
        created_response = client.post("/claims/", json=claim_data)
        claim_id = created_response.json()["id"]

        # Transition to VALIDATED
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.VALIDATED.value, "reason": "Test"},
        )

        # Filter by CREATED status
        response = client.get("/claims/?status_filter=CREATED")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(claim["status"] == ClaimStatus.CREATED.value for claim in data)

        # Filter by VALIDATED status
        response = client.get("/claims/?status_filter=VALIDATED")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(claim["status"] == ClaimStatus.VALIDATED.value for claim in data)

    def test_transition_claim_state_valid(self, client, sample_claim):
        """Test valid state transition."""
        claim_id = sample_claim.id
        assert sample_claim.status == ClaimStatus.CREATED.value

        response = client.post(
            f"/claims/{claim_id}/transition",
            json={
                "target_status": ClaimStatus.VALIDATED.value,
                "reason": "Validation completed",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ClaimStatus.VALIDATED.value

    def test_transition_claim_state_invalid(self, client, sample_claim):
        """Test invalid state transition returns error."""
        claim_id = sample_claim.id

        # Try to go directly from CREATED to PAID (invalid)
        response = client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.PAID.value, "reason": "Invalid transition"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot transition" in response.json()["detail"].lower()

    def test_get_claim_transitions(self, client, sample_claim):
        """Test retrieving claim transition history."""
        claim_id = sample_claim.id

        # Make some transitions
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.VALIDATED.value, "reason": "Step 1"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.SUBMITTED.value, "reason": "Step 2"},
        )

        response = client.get(f"/claims/{claim_id}/transitions")
        assert response.status_code == status.HTTP_200_OK
        transitions = response.json()
        assert len(transitions) >= 3  # Initial CREATED + 2 transitions
        assert all("to_status" in t for t in transitions)
        assert all("transition_reason" in t for t in transitions)

    def test_get_valid_next_states(self, client, sample_claim):
        """Test getting valid next states for a claim."""
        claim_id = sample_claim.id

        response = client.get(f"/claims/{claim_id}/next-states")
        assert response.status_code == status.HTTP_200_OK
        next_states = response.json()
        assert isinstance(next_states, list)
        assert ClaimStatus.VALIDATED.value in next_states

    def test_update_claim(self, client, sample_claim):
        """Test updating claim fields."""
        claim_id = sample_claim.id
        new_amount = 2500.00

        response = client.patch(
            f"/claims/{claim_id}",
            json={"amount": new_amount},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["amount"] == new_amount
        # Status should not change
        assert data["status"] == sample_claim.status

    def test_create_claim_full_lifecycle(self, client, sample_claim_data):
        """Test a complete claim lifecycle through API."""
        # Create claim
        create_response = client.post("/claims/", json=sample_claim_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        claim_id = create_response.json()["id"]

        # Transition: CREATED -> VALIDATED
        response = client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.VALIDATED.value, "reason": "Validated"},
        )
        assert response.status_code == status.HTTP_200_OK

        # Transition: VALIDATED -> SUBMITTED
        response = client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.SUBMITTED.value, "reason": "Submitted to payer"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["submitted_at"] is not None

        # Transition: SUBMITTED -> ACCEPTED
        response = client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.ACCEPTED.value, "reason": "Payer accepted"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["responded_at"] is not None

        # Transition: ACCEPTED -> PAID
        response = client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.PAID.value, "reason": "Payment received"},
        )
        assert response.status_code == status.HTTP_200_OK
        final_claim = response.json()
        assert final_claim["status"] == ClaimStatus.PAID.value
        assert final_claim["paid_at"] is not None

        # Verify transition history
        transitions_response = client.get(f"/claims/{claim_id}/transitions")
        transitions = transitions_response.json()
        assert len(transitions) == 5  # CREATED, VALIDATED, SUBMITTED, ACCEPTED, PAID

    def test_denial_workflow(self, client, sample_claim_data):
        """Test denial and resubmission workflow."""
        # Create and submit claim
        create_response = client.post("/claims/", json=sample_claim_data)
        claim_id = create_response.json()["id"]

        # Move to SUBMITTED
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.VALIDATED.value, "reason": "Validated"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.SUBMITTED.value, "reason": "Submitted"},
        )

        # Deny the claim
        response = client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.DENIED.value, "reason": "Denied by payer"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == ClaimStatus.DENIED.value

        # Update with denial details
        response = client.patch(
            f"/claims/{claim_id}",
            json={
                "denial_reason": "INVALID_CPT_CODE",
                "denial_details": "CPT code not covered",
            },
        )
        assert response.status_code == status.HTTP_200_OK

        # Resubmit the claim
        response = client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.RESUBMITTED.value, "reason": "Resubmitted"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == ClaimStatus.RESUBMITTED.value

        # Can transition from RESUBMITTED to ACCEPTED or DENIED
        next_states = client.get(f"/claims/{claim_id}/next-states").json()
        assert ClaimStatus.ACCEPTED.value in next_states
        assert ClaimStatus.DENIED.value in next_states
