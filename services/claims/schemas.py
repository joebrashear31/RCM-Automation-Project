"""Pydantic schemas for claims API."""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional
from common.enums import ClaimStatus, PayerType, DenialReason, EventType, DenialCategory, RecommendedAction, AgentDecision


class ClaimCreate(BaseModel):
    """Schema for creating a new claim."""

    claim_number: str = Field(..., min_length=1, max_length=50)
    provider_npi: str = Field(..., min_length=10, max_length=10)
    patient_id: str = Field(..., min_length=1)
    payer_id: str = Field(..., min_length=1)
    payer_type: PayerType
    amount: float = Field(..., gt=0)
    cpt_codes: List[str] = Field(..., min_items=1)
    icd_codes: List[str] = Field(..., min_items=1)
    service_date_from: datetime
    service_date_to: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimUpdate(BaseModel):
    """Schema for updating claim fields (limited)."""

    amount: Optional[float] = Field(None, gt=0)
    denial_reason: Optional[DenialReason] = None
    denial_details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClaimStateTransitionResponse(BaseModel):
    """Schema for state transition audit record."""

    id: int
    claim_id: int
    from_status: Optional[str]
    to_status: str
    transition_reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimResponse(BaseModel):
    """Schema for claim response."""

    id: int
    claim_number: str
    provider_npi: str
    patient_id: str
    payer_id: str
    payer_type: str
    status: str
    amount: float
    allowed_amount: Optional[float]
    paid_amount: Optional[float]
    cpt_codes: List[str]
    icd_codes: List[str]
    service_date_from: datetime
    service_date_to: datetime
    submitted_at: Optional[datetime]
    responded_at: Optional[datetime]
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    denial_reason: Optional[str]
    denial_details: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class StateTransitionRequest(BaseModel):
    """Schema for requesting a state transition."""

    target_status: ClaimStatus
    reason: Optional[str] = None


class ClaimEventResponse(BaseModel):
    """Schema for claim event response."""

    id: int
    claim_id: int
    event_type: str
    event_data: Optional[dict]
    description: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DenialEventResponse(BaseModel):
    """Schema for denial event response."""

    id: int
    claim_id: int
    payer_id: str
    payer_type: str
    denial_reason_code: str
    denial_reason_text: str
    denial_category: Optional[str]
    raw_payer_payload: Optional[dict]
    recommended_action: Optional[str]
    classification_confidence: Optional[float]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DenialEventCreate(BaseModel):
    """Schema for creating a denial event."""

    payer_id: str
    payer_type: str
    denial_reason_code: str
    denial_reason_text: str
    raw_payer_payload: Optional[dict] = None


class AgentDecisionResponse(BaseModel):
    """Schema for agent decision response."""

    id: int
    claim_id: int
    decision: str
    confidence: float
    rationale: str
    missing_info: Optional[List[str]]
    denial_category: Optional[str]
    rule_based_recommendation: Optional[str]
    was_executed: str
    requires_human_review: str
    human_override: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HumanOverrideRequest(BaseModel):
    """Schema for human override request."""

    override_action: AgentDecision
    reviewer: str = Field(..., min_length=1)
    notes: Optional[str] = None

