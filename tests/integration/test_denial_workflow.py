"""Integration tests for denial handling workflow."""

import pytest
from fastapi import status
from common.enums import (
    ClaimStatus,
    DenialCategory,
    PayerType,
    AgentDecision as AgentDecisionEnum,
)


class TestDenialWorkflow:
    """Test complete denial handling workflow."""

    def test_create_denial_event(self, client, sample_claim):
        """Test creating a denial event."""
        claim_id = sample_claim.id

        # Move claim to DENIED state first
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.VALIDATED.value, "reason": "Validate"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.SUBMITTED.value, "reason": "Submit"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.DENIED.value, "reason": "Denied"},
        )

        # Create denial event
        response = client.post(
            f"/claims/{claim_id}/denials",
            json={
                "payer_id": "PAY-001",
                "payer_type": PayerType.COMMERCIAL.value,
                "denial_reason_code": "CO-50",
                "denial_reason_text": "Invalid CPT code",
                "raw_payer_payload": {"code": "CO-50", "message": "Invalid CPT code"},
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["denial_reason_code"] == "CO-50"
        assert data["denial_category"] == DenialCategory.CODING_ERROR.value
        assert data["recommended_action"] is not None

    def test_process_denial_with_agent(self, client, sample_claim):
        """Test processing denial with agent decision-making."""
        claim_id = sample_claim.id

        # Move to DENIED state
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.VALIDATED.value, "reason": "Validate"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.SUBMITTED.value, "reason": "Submit"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.DENIED.value, "reason": "Denied"},
        )

        # Create denial event
        client.post(
            f"/claims/{claim_id}/denials",
            json={
                "payer_id": "PAY-001",
                "payer_type": PayerType.COMMERCIAL.value,
                "denial_reason_code": "CO-50",
                "denial_reason_text": "Invalid CPT code",
            },
        )

        # Process with agent
        response = client.post(
            f"/claims/{claim_id}/process-denial?denial_category=CODING_ERROR&confidence_threshold=0.7&auto_execute=false",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["decision"] is not None
        assert data["confidence"] is not None
        assert data["rationale"] is not None
        assert float(data["confidence"]) >= 0.0
        assert float(data["confidence"]) <= 1.0

    def test_execute_agent_decision(self, client, sample_claim):
        """Test executing an agent decision."""
        claim_id = sample_claim.id

        # Move to DENIED state
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.VALIDATED.value, "reason": "Validate"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.SUBMITTED.value, "reason": "Submit"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.DENIED.value, "reason": "Denied"},
        )

        # Process denial with agent
        process_response = client.post(
            f"/claims/{claim_id}/process-denial?denial_category=CODING_ERROR&auto_execute=false",
        )
        decision_id = process_response.json()["id"]

        # Execute the decision
        execute_response = client.post(f"/claims/{claim_id}/execute-decision/{decision_id}")

        assert execute_response.status_code == status.HTTP_200_OK
        data = execute_response.json()
        assert data["status"] in ["success", "already_executed"]

    def test_human_override(self, client, sample_claim):
        """Test human override of agent decision."""
        claim_id = sample_claim.id

        # Move to DENIED state
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.VALIDATED.value, "reason": "Validate"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.SUBMITTED.value, "reason": "Submit"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.DENIED.value, "reason": "Denied"},
        )

        # Process denial with agent
        process_response = client.post(
            f"/claims/{claim_id}/process-denial?denial_category=ELIGIBILITY&auto_execute=false",
        )
        decision_id = process_response.json()["id"]

        # Override the decision
        override_response = client.post(
            f"/claims/{claim_id}/override-decision/{decision_id}",
            json={
                "override_action": AgentDecisionEnum.APPEAL.value,
                "reviewer": "john.doe@example.com",
                "notes": "Believe appeal has merit",
            },
        )

        assert override_response.status_code == status.HTTP_200_OK
        data = override_response.json()
        assert data["status"] == "success"
        assert data["override_action"] == AgentDecisionEnum.APPEAL.value

    def test_get_denial_events(self, client, sample_claim):
        """Test retrieving denial events for a claim."""
        claim_id = sample_claim.id

        # Create denial event
        client.post(
            f"/claims/{claim_id}/denials",
            json={
                "payer_id": "PAY-001",
                "payer_type": PayerType.COMMERCIAL.value,
                "denial_reason_code": "CO-50",
                "denial_reason_text": "Invalid CPT code",
            },
        )

        # Get denial events
        response = client.get(f"/claims/{claim_id}/denials")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert data[0]["denial_reason_code"] == "CO-50"

    def test_get_agent_decisions(self, client, sample_claim):
        """Test retrieving agent decisions for a claim."""
        claim_id = sample_claim.id

        # Process denial with agent
        client.post(
            f"/claims/{claim_id}/process-denial?denial_category=CODING_ERROR&auto_execute=false",
        )

        # Get agent decisions
        response = client.get(f"/claims/{claim_id}/agent-decisions")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert data[0]["decision"] is not None
        assert data[0]["confidence"] is not None

    def test_get_claim_events(self, client, sample_claim):
        """Test retrieving all events for a claim."""
        claim_id = sample_claim.id

        # Create some events by processing
        client.post(
            f"/claims/{claim_id}/process-denial?denial_category=CODING_ERROR&auto_execute=false",
        )

        # Get events
        response = client.get(f"/claims/{claim_id}/events")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert all("event_type" in event for event in data)

    def test_complete_denial_workflow(self, client, sample_claim_data):
        """Test complete workflow from denial to resolution."""
        # Create claim
        create_response = client.post("/claims/", json=sample_claim_data)
        claim_id = create_response.json()["id"]

        # Move through states
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.VALIDATED.value, "reason": "Validate"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.SUBMITTED.value, "reason": "Submit"},
        )
        client.post(
            f"/claims/{claim_id}/transition",
            json={"target_status": ClaimStatus.DENIED.value, "reason": "Denied"},
        )

        # Create denial event
        denial_response = client.post(
            f"/claims/{claim_id}/denials",
            json={
                "payer_id": "PAY-001",
                "payer_type": PayerType.COMMERCIAL.value,
                "denial_reason_code": "CO-50",
                "denial_reason_text": "Invalid CPT code - should be 99214",
            },
        )
        assert denial_response.json()["denial_category"] == DenialCategory.CODING_ERROR.value

        # Process with agent
        agent_response = client.post(
            f"/claims/{claim_id}/process-denial?denial_category=CODING_ERROR&auto_execute=false",
        )
        decision_id = agent_response.json()["id"]
        assert agent_response.json()["decision"] == AgentDecisionEnum.RESUBMIT.value

        # Execute decision (resubmit)
        execute_response = client.post(f"/claims/{claim_id}/execute-decision/{decision_id}")
        assert execute_response.status_code == status.HTTP_200_OK

        # Verify claim is resubmitted
        claim_response = client.get(f"/claims/{claim_id}")
        assert claim_response.json()["status"] == ClaimStatus.RESUBMITTED.value

        # Verify events were created
        events_response = client.get(f"/claims/{claim_id}/events")
        events = events_response.json()
        event_types = [e["event_type"] for e in events]
        assert "CLAIM_DENIED" in event_types
        assert "AGENT_DECISION" in event_types
