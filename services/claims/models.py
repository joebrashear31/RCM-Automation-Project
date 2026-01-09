"""SQLAlchemy models for claims."""

from sqlalchemy import Column, String, Numeric, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from common.db import Base
from common.enums import ClaimStatus, PayerType, EventType, DenialCategory, RecommendedAction, AgentDecision

# everything in a claim
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

    # Agent and workflow fields
    recommended_action = Column(String(30), nullable=True)  # RecommendedAction enum value
    agent_confidence = Column(Numeric(3, 2), nullable=True)  # 0.00 to 1.00
    requires_human_review = Column(String(5), default="false", nullable=False)  # Boolean as string for simplicity
    
    # Relationships
    state_transitions = relationship("ClaimStateTransition", back_populates="claim", cascade="all, delete-orphan")
    events = relationship("ClaimEvent", back_populates="claim", cascade="all, delete-orphan", order_by="ClaimEvent.created_at")
    denial_events = relationship("DenialEvent", back_populates="claim", cascade="all, delete-orphan", order_by="DenialEvent.created_at")
    agent_decisions = relationship("AgentDecision", back_populates="claim", cascade="all, delete-orphan", order_by="AgentDecision.created_at")

# transitioning the claim states
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


class ClaimEvent(Base):
    """Immutable event log for all claim-related events."""

    __tablename__ = "claim_events"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    event_type = Column(String(30), nullable=False, index=True)  # EventType enum value
    event_data = Column(JSON, nullable=True)  # Flexible JSON for event-specific data
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    claim = relationship("Claim", back_populates="events")


class DenialEvent(Base):
    """Immutable denial event log with full payer response details."""

    __tablename__ = "denial_events"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    
    # Payer information
    payer_id = Column(String(50), nullable=False)
    payer_type = Column(String(20), nullable=False)
    
    # Denial details
    denial_reason_code = Column(String(20), nullable=False)  # e.g., CO-50, CO-97
    denial_reason_text = Column(Text, nullable=False)  # Human-readable explanation
    denial_category = Column(String(30), nullable=True)  # DenialCategory enum value
    
    # Raw payer response (immutable record)
    raw_payer_payload = Column(JSON, nullable=True)  # Full JSON from payer
    
    # Classification
    recommended_action = Column(String(30), nullable=True)  # RecommendedAction enum value
    classification_confidence = Column(Numeric(3, 2), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    claim = relationship("Claim", back_populates="denial_events")


class AgentDecision(Base):
    """Immutable log of all agent decisions for auditability."""

    __tablename__ = "agent_decisions"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    
    # Decision details
    decision = Column(String(30), nullable=False)  # AgentDecision enum value
    confidence = Column(Numeric(3, 2), nullable=False)  # 0.00 to 1.00
    rationale = Column(Text, nullable=False)
    missing_info = Column(JSON, nullable=True)  # List of missing information fields
    
    # Context used for decision
    denial_category = Column(String(30), nullable=True)
    payer_type = Column(String(20), nullable=True)
    rule_based_recommendation = Column(String(30), nullable=True)
    historical_success_rate = Column(Numeric(5, 4), nullable=True)
    
    # Full prompt and response (for transparency)
    agent_prompt = Column(Text, nullable=True)  # Full prompt sent to agent
    agent_response_raw = Column(JSON, nullable=True)  # Raw agent response
    
    # Execution
    was_executed = Column(String(5), default="false", nullable=False)  # Boolean as string
    executed_action = Column(String(50), nullable=True)
    execution_result = Column(Text, nullable=True)
    
    # Human interaction
    requires_human_review = Column(String(5), default="false", nullable=False)
    human_override = Column(String(5), default="false", nullable=False)
    human_reviewer = Column(String(100), nullable=True)
    human_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    claim = relationship("Claim", back_populates="agent_decisions")


class OutcomeTracking(Base):
    """Tracks outcomes of denial resolution actions for learning loop."""

    __tablename__ = "outcome_tracking"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    agent_decision_id = Column(Integer, ForeignKey("agent_decisions.id"), nullable=True, index=True)
    
    # Action taken
    action_taken = Column(String(30), nullable=False)  # AgentDecision enum value
    denial_category = Column(String(30), nullable=False)  # DenialCategory enum value
    
    # Outcome
    outcome = Column(String(20), nullable=False)  # SUCCESS, FAILURE, PENDING
    final_status = Column(String(20), nullable=True)  # Final claim status
    
    # Financial metrics
    revenue_recovered = Column(Numeric(10, 2), nullable=True)  # Amount recovered
    time_to_resolution_days = Column(Integer, nullable=True)  # Days to resolution
    
    # Success metrics
    appeal_successful = Column(String(5), nullable=True)  # Boolean as string
    resubmission_successful = Column(String(5), nullable=True)  # Boolean as string
    
    # Learning data
    outcome_date = Column(DateTime, nullable=True)  # When outcome was determined
    human_feedback = Column(Text, nullable=True)  # Human feedback on decision quality
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

