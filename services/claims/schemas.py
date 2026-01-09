"""Pydantic schemas for claims API."""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional
from common.enums import ClaimStatus, PayerType, DenialReason


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

