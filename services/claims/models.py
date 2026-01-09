"""SQLAlchemy models for claims."""

from sqlalchemy import Column, String, Numeric, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from common.db import Base
from common.enums import ClaimStatus, PayerType


class Claim(Base):
    """Medical claim entity."""

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_number = Column(String(50), unique=True, index=True, nullable=False)
    provider_npi = Column(String(10), nullable=False)
    patient_id = Column(String(50), nullable=False, index=True)
    payer_id = Column(String(50), nullable=False, index=True)
    payer_type = Column(String(20), nullable=False)

    status = Column(String(20), default=ClaimStatus.CREATED, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    allowed_amount = Column(Numeric(10, 2), nullable=True)
    paid_amount = Column(Numeric(10, 2), nullable=True)

    # CPT and ICD codes
    cpt_codes = Column(JSON, nullable=False)  # List of CPT codes
    icd_codes = Column(JSON, nullable=False)  # List of ICD-10 codes

    # Service dates
    service_date_from = Column(DateTime, nullable=False)
    service_date_to = Column(DateTime, nullable=False)

    # Submission and response dates
    submitted_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Denial information
    denial_reason = Column(String(50), nullable=True)
    denial_details = Column(Text, nullable=True)

    # Relationships
    state_transitions = relationship("ClaimStateTransition", back_populates="claim", cascade="all, delete-orphan")


class ClaimStateTransition(Base):
    """Audit trail for claim state changes."""

    __tablename__ = "claim_state_transitions"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    transition_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    claim = relationship("Claim", back_populates="state_transitions")

