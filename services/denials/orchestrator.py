"""Workflow Orchestrator - Executes agent decisions and manages denial workflows.

The orchestrator:
- Takes agent decisions
- Executes actions (state transitions, workflows)
- Handles human-in-the-loop logic
- Tracks outcomes
"""

from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from common.enums import (
    AgentDecision as AgentDecisionEnum,
    ClaimStatus,
    EventType,
    RecommendedAction,
)
from services.claims.models import Claim, ClaimEvent, AgentDecision as AgentDecisionModel
from services.claims.state_machine import ClaimStateMachine, StateMachineError
from services.denials.agent import make_agent_decision
from services.denials.classifier import get_recommended_action
from common.enums import DenialCategory, PayerType
import logging

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates denial resolution workflows based on agent decisions."""

    # Confidence thresholds for human review
    DEFAULT_CONFIDENCE_THRESHOLD = 0.7

    @classmethod
    def process_denial(
        cls,
        db: Session,
        claim: Claim,
        denial_category: DenialCategory,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        auto_execute: bool = False,
    ) -> Tuple[AgentDecisionModel, bool]:
        """
        Process a denial by getting agent decision and optionally executing it.
        
        Args:
            db: Database session
            claim: The denied claim
            denial_category: Category of the denial
            confidence_threshold: Minimum confidence to auto-execute
            auto_execute: Whether to automatically execute high-confidence decisions
            
        Returns:
            Tuple of (agent_decision_record, was_executed)
        """
        # Get rule-based recommendation
        rule_recommendation = get_recommended_action(denial_category)
        
        # Get historical success rate (simplified - in production, query from outcomes)
        historical_success_rate = cls._get_historical_success_rate(
            db, denial_category, rule_recommendation
        )
        
        # Prepare claim data for agent
        claim_data = {
            "amount": float(claim.amount),
            "cpt_codes": claim.cpt_codes,
            "icd_codes": claim.icd_codes,
            "payer_type": claim.payer_type,
            "denial_reason": claim.denial_reason,
        }
        
        # Get agent decision (stateless - no DB writes)
        agent_result = make_agent_decision(
            claim_data=claim_data,
            denial_category=denial_category,
            payer_type=PayerType(claim.payer_type),
            rule_based_recommendation=rule_recommendation,
            historical_success_rate=historical_success_rate,
        )
        
        # Log agent decision (immutable audit trail)
        agent_decision = AgentDecisionModel(
            claim_id=claim.id,
            decision=agent_result.decision.value,
            confidence=float(agent_result.confidence),
            rationale=agent_result.rationale,
            missing_info=agent_result.missing_info,
            denial_category=denial_category.value,
            payer_type=claim.payer_type,
            rule_based_recommendation=rule_recommendation.value,
            historical_success_rate=historical_success_rate,
            requires_human_review=(
                "true" if agent_result.confidence < confidence_threshold else "false"
            ),
        )
        
        db.add(agent_decision)
        db.flush()  # Get ID without committing
        
        # Create event
        event = ClaimEvent(
            claim_id=claim.id,
            event_type=EventType.AGENT_DECISION.value,
            event_data={
                "decision": agent_result.decision.value,
                "confidence": float(agent_result.confidence),
                "requires_review": agent_result.confidence < confidence_threshold,
            },
            description=f"Agent decision: {agent_result.decision.value}",
        )
        db.add(event)
        
        # Update claim with recommendation and confidence
        claim.recommended_action = rule_recommendation.value
        claim.agent_confidence = float(agent_result.confidence)
        claim.requires_human_review = (
            "true" if agent_result.confidence < confidence_threshold else "false"
        )
        
        was_executed = False
        
        # Auto-execute if confidence is high enough and auto_execute is enabled
        if auto_execute and agent_result.confidence >= confidence_threshold:
            try:
                execution_result = cls._execute_decision(db, claim, agent_result.decision)
                agent_decision.was_executed = "true"
                agent_decision.executed_action = execution_result["action"]
                agent_decision.execution_result = execution_result["result"]
                was_executed = True
                logger.info(
                    f"Auto-executed agent decision {agent_result.decision.value} "
                    f"for claim {claim.id} with confidence {agent_result.confidence:.2f}"
                )
            except Exception as e:
                agent_decision.execution_result = f"Execution failed: {str(e)}"
                logger.error(f"Failed to execute agent decision for claim {claim.id}: {e}")
        
        db.commit()
        db.refresh(agent_decision)
        
        return agent_decision, was_executed

    @classmethod
    def execute_agent_decision(
        cls, db: Session, claim: Claim, agent_decision_id: int
    ) -> Dict:
        """Execute a previously made agent decision."""
        agent_decision = (
            db.query(AgentDecisionModel)
            .filter(AgentDecisionModel.id == agent_decision_id)
            .first()
        )
        
        if not agent_decision:
            raise ValueError(f"Agent decision {agent_decision_id} not found")
        
        if agent_decision.claim_id != claim.id:
            raise ValueError("Agent decision does not belong to this claim")
        
        if agent_decision.was_executed == "true":
            return {
                "status": "already_executed",
                "message": "This decision was already executed",
                "execution_result": agent_decision.execution_result,
            }
        
        try:
            decision_enum = AgentDecisionEnum(agent_decision.decision)
            execution_result = cls._execute_decision(db, claim, decision_enum)
            
            agent_decision.was_executed = "true"
            agent_decision.executed_action = execution_result["action"]
            agent_decision.execution_result = execution_result["result"]
            
            db.commit()
            
            return {
                "status": "success",
                "execution_result": execution_result,
            }
        except Exception as e:
            agent_decision.execution_result = f"Execution failed: {str(e)}"
            db.commit()
            return {
                "status": "error",
                "error": str(e),
            }

    @classmethod
    def _execute_decision(
        cls, db: Session, claim: Claim, decision: AgentDecisionEnum
    ) -> Dict:
        """Execute a specific decision action."""
        if decision == AgentDecisionEnum.RESUBMIT:
            # Transition to RESUBMITTED
            updated_claim, _ = ClaimStateMachine.transition(
                db=db,
                claim=claim,
                target_status=ClaimStatus.RESUBMITTED,
                reason="Agent decision: Resubmit after fixing issues",
            )
            # Record outcome tracking
            from services.denials.outcomes import OutcomeTracker
            denial_category = DenialCategory(claim.denial_events[-1].denial_category) if claim.denial_events else DenialCategory.UNKNOWN
            OutcomeTracker.record_outcome(
                db=db,
                claim=updated_claim,
                action_taken=decision,
                denial_category=denial_category,
                outcome="PENDING",
            )
            return {
                "action": "resubmitted",
                "result": f"Claim transitioned to {ClaimStatus.RESUBMITTED.value}",
            }
        
        elif decision == AgentDecisionEnum.APPEAL:
            # Transition to APPEAL_PENDING
            updated_claim, _ = ClaimStateMachine.transition(
                db=db,
                claim=claim,
                target_status=ClaimStatus.APPEAL_PENDING,
                reason="Agent decision: File appeal",
            )
            # Record outcome tracking
            from services.denials.outcomes import OutcomeTracker
            denial_category = DenialCategory(claim.denial_events[-1].denial_category) if claim.denial_events else DenialCategory.UNKNOWN
            OutcomeTracker.record_outcome(
                db=db,
                claim=updated_claim,
                action_taken=decision,
                denial_category=denial_category,
                outcome="PENDING",
            )
            return {
                "action": "appeal_filed",
                "result": f"Claim transitioned to {ClaimStatus.APPEAL_PENDING.value}",
            }
        
        elif decision == AgentDecisionEnum.WRITE_OFF:
            # Transition to WRITE_OFF
            updated_claim, _ = ClaimStateMachine.transition(
                db=db,
                claim=claim,
                target_status=ClaimStatus.WRITE_OFF,
                reason="Agent decision: Write off as uncollectible",
            )
            # Record outcome tracking
            from services.denials.outcomes import OutcomeTracker
            denial_category = DenialCategory(claim.denial_events[-1].denial_category) if claim.denial_events else DenialCategory.UNKNOWN
            OutcomeTracker.record_outcome(
                db=db,
                claim=updated_claim,
                action_taken=decision,
                denial_category=denial_category,
                outcome="FAILURE",
                revenue_recovered=0.0,
            )
            return {
                "action": "written_off",
                "result": f"Claim transitioned to {ClaimStatus.WRITE_OFF.value}",
            }
        
        elif decision == AgentDecisionEnum.REQUEST_AUTH:
            # Don't transition state, but create event
            event = ClaimEvent(
                claim_id=claim.id,
                event_type=EventType.WORKFLOW_EXECUTED.value,
                event_data={"action": "request_authorization"},
                description="Agent decision: Request prior authorization",
            )
            db.add(event)
            db.commit()
            return {
                "action": "authorization_requested",
                "result": "Authorization request workflow initiated",
            }
        
        elif decision == AgentDecisionEnum.COLLECT_PATIENT:
            # Don't transition state, but create event
            event = ClaimEvent(
                claim_id=claim.id,
                event_type=EventType.WORKFLOW_EXECUTED.value,
                event_data={"action": "collect_from_patient"},
                description="Agent decision: Bill patient directly",
            )
            db.add(event)
            db.commit()
            return {
                "action": "patient_billing_initiated",
                "result": "Patient billing workflow initiated",
            }
        
        elif decision == AgentDecisionEnum.FLAG_FOR_HUMAN:
            # Already flagged, no action needed
            return {
                "action": "flagged",
                "result": "Claim flagged for human review",
            }
        
        else:
            return {
                "action": "no_action",
                "result": f"No action taken for decision: {decision.value}",
            }

    @classmethod
    def _get_historical_success_rate(
        cls,
        db: Session,
        denial_category: DenialCategory,
        recommended_action: RecommendedAction,
    ) -> Optional[float]:
        """
        Get historical success rate for a category/action combination.
        
        Uses outcome tracking data for learning loop.
        """
        from services.denials.outcomes import OutcomeTracker
        from common.enums import AgentDecision as AgentDecisionEnum
        
        # Map RecommendedAction to AgentDecisionEnum for lookup
        action_mapping = {
            RecommendedAction.RESUBMIT: AgentDecisionEnum.RESUBMIT,
            RecommendedAction.APPEAL: AgentDecisionEnum.APPEAL,
            RecommendedAction.WRITE_OFF: AgentDecisionEnum.WRITE_OFF,
            RecommendedAction.REQUEST_AUTH: AgentDecisionEnum.REQUEST_AUTH,
        }
        
        agent_action = action_mapping.get(recommended_action)
        if not agent_action:
            return None
        
        return OutcomeTracker.get_success_rate(
            db=db,
            denial_category=denial_category,
            action_taken=agent_action,
        )

    @classmethod
    def human_override(
        cls,
        db: Session,
        claim: Claim,
        agent_decision_id: int,
        override_action: AgentDecisionEnum,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> Dict:
        """Handle human override of an agent decision."""
        agent_decision = (
            db.query(AgentDecisionModel)
            .filter(AgentDecisionModel.id == agent_decision_id)
            .first()
        )
        
        if not agent_decision:
            raise ValueError(f"Agent decision {agent_decision_id} not found")
        
        agent_decision.human_override = "true"
        agent_decision.human_reviewer = reviewer
        agent_decision.human_notes = notes
        
        # Execute the override action
        execution_result = cls._execute_decision(db, claim, override_action)
        
        agent_decision.was_executed = "true"
        agent_decision.executed_action = execution_result["action"]
        agent_decision.execution_result = (
            f"Human override: {execution_result['result']}"
        )
        
        # Create event
        event = ClaimEvent(
            claim_id=claim.id,
            event_type=EventType.HUMAN_OVERRIDE.value,
            event_data={
                "agent_decision_id": agent_decision_id,
                "override_action": override_action.value,
                "reviewer": reviewer,
            },
            description=f"Human override: {override_action.value}",
        )
        db.add(event)
        db.commit()
        
        return {
            "status": "success",
            "override_action": override_action.value,
            "execution_result": execution_result,
        }
