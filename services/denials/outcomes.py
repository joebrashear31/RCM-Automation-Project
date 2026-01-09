"""Outcome Tracking and Learning Loop for Denial Resolution.

Tracks outcomes of agent decisions to improve future decision-making.
"""

from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from common.enums import DenialCategory, AgentDecision as AgentDecisionEnum, ClaimStatus
from services.claims.models import OutcomeTracking, Claim, AgentDecision as AgentDecisionModel
import logging

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """Tracks and analyzes outcomes of denial resolution actions."""

    @classmethod
    def record_outcome(
        cls,
        db: Session,
        claim: Claim,
        action_taken: AgentDecisionEnum,
        denial_category: DenialCategory,
        agent_decision_id: Optional[int] = None,
        outcome: str = "PENDING",
        revenue_recovered: Optional[float] = None,
        appeal_successful: Optional[bool] = None,
        resubmission_successful: Optional[bool] = None,
        human_feedback: Optional[str] = None,
    ) -> OutcomeTracking:
        """
        Record the outcome of a denial resolution action.
        
        Args:
            db: Database session
            claim: The claim
            action_taken: Action that was taken
            denial_category: Category of the denial
            agent_decision_id: ID of the agent decision (if applicable)
            outcome: SUCCESS, FAILURE, or PENDING
            revenue_recovered: Amount of revenue recovered
            appeal_successful: Whether appeal was successful
            resubmission_successful: Whether resubmission was successful
            human_feedback: Human feedback on decision quality
            
        Returns:
            OutcomeTracking record
        """
        # Calculate time to resolution
        time_to_resolution = None
        if claim.responded_at and claim.status in [ClaimStatus.PAID, ClaimStatus.WRITE_OFF]:
            # If resolved, calculate days
            if claim.paid_at:
                time_to_resolution = (claim.paid_at - claim.responded_at).days
            elif claim.updated_at:
                time_to_resolution = (claim.updated_at - claim.responded_at).days
        
        # Determine revenue recovered
        if revenue_recovered is None:
            if claim.status == ClaimStatus.PAID and claim.paid_amount:
                revenue_recovered = float(claim.paid_amount)
            elif claim.status == ClaimStatus.WRITE_OFF:
                revenue_recovered = 0.0
        
        outcome_record = OutcomeTracking(
            claim_id=claim.id,
            agent_decision_id=agent_decision_id,
            action_taken=action_taken.value,
            denial_category=denial_category.value,
            outcome=outcome,
            final_status=claim.status,
            revenue_recovered=revenue_recovered,
            time_to_resolution_days=time_to_resolution,
            appeal_successful="true" if appeal_successful else "false" if appeal_successful is False else None,
            resubmission_successful="true" if resubmission_successful else "false" if resubmission_successful is False else None,
            outcome_date=datetime.utcnow() if outcome != "PENDING" else None,
            human_feedback=human_feedback,
        )
        
        db.add(outcome_record)
        db.commit()
        db.refresh(outcome_record)
        
        logger.info(
            f"Recorded outcome for claim {claim.id}: {outcome} "
            f"(action: {action_taken.value}, category: {denial_category.value})"
        )
        
        return outcome_record

    @classmethod
    def get_success_rate(
        cls,
        db: Session,
        denial_category: Optional[DenialCategory] = None,
        action_taken: Optional[AgentDecisionEnum] = None,
        days_back: int = 90,
    ) -> Optional[float]:
        """
        Get historical success rate for a category/action combination.
        
        Args:
            db: Database session
            denial_category: Optional category filter
            action_taken: Optional action filter
            days_back: Number of days to look back
            
        Returns:
            Success rate (0.0 to 1.0) or None if insufficient data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        query = db.query(OutcomeTracking).filter(
            OutcomeTracking.created_at >= cutoff_date,
            OutcomeTracking.outcome != "PENDING",
        )
        
        if denial_category:
            query = query.filter(OutcomeTracking.denial_category == denial_category.value)
        
        if action_taken:
            query = query.filter(OutcomeTracking.action_taken == action_taken.value)
        
        outcomes = query.all()
        
        if len(outcomes) < 5:  # Need at least 5 data points
            return None
        
        successful = sum(1 for o in outcomes if o.outcome == "SUCCESS")
        success_rate = successful / len(outcomes)
        
        return success_rate

    @classmethod
    def get_revenue_metrics(
        cls,
        db: Session,
        days_back: int = 90,
    ) -> Dict:
        """
        Get revenue recovery metrics.
        
        Returns:
            Dictionary with revenue metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        outcomes = (
            db.query(OutcomeTracking)
            .filter(
                OutcomeTracking.created_at >= cutoff_date,
                OutcomeTracking.outcome == "SUCCESS",
            )
            .all()
        )
        
        total_recovered = sum(float(o.revenue_recovered or 0) for o in outcomes)
        total_denied = (
            db.query(func.sum(Claim.amount))
            .filter(
                Claim.status.in_([ClaimStatus.DENIED, ClaimStatus.REJECTED]),
                Claim.created_at >= cutoff_date,
            )
            .scalar() or 0
        )
        
        recovery_rate = (total_recovered / float(total_denied)) if total_denied > 0 else 0.0
        
        return {
            "total_revenue_recovered": total_recovered,
            "total_denied_amount": float(total_denied),
            "recovery_rate": recovery_rate,
            "total_resolved": len(outcomes),
        }

    @classmethod
    def get_learning_insights(
        cls,
        db: Session,
        denial_category: DenialCategory,
        days_back: int = 90,
    ) -> Dict:
        """
        Get insights for improving decisions in a specific category.
        
        Returns:
            Dictionary with insights and recommendations
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        outcomes = (
            db.query(OutcomeTracking)
            .filter(
                OutcomeTracking.denial_category == denial_category.value,
                OutcomeTracking.created_at >= cutoff_date,
                OutcomeTracking.outcome != "PENDING",
            )
            .all()
        )
        
        if not outcomes:
            return {
                "insufficient_data": True,
                "message": "Not enough historical data for this category",
            }
        
        # Calculate success rates by action
        actions = {}
        for outcome in outcomes:
            action = outcome.action_taken
            if action not in actions:
                actions[action] = {"total": 0, "success": 0, "revenue": 0.0}
            
            actions[action]["total"] += 1
            if outcome.outcome == "SUCCESS":
                actions[action]["success"] += 1
            if outcome.revenue_recovered:
                actions[action]["revenue"] += float(outcome.revenue_recovered)
        
        # Find best performing action
        best_action = None
        best_rate = 0.0
        for action, stats in actions.items():
            rate = stats["success"] / stats["total"]
            if rate > best_rate:
                best_rate = rate
                best_action = action
        
        return {
            "denial_category": denial_category.value,
            "total_outcomes": len(outcomes),
            "best_action": best_action,
            "best_action_success_rate": best_rate,
            "actions_breakdown": {
                action: {
                    "success_rate": stats["success"] / stats["total"],
                    "total_attempts": stats["total"],
                    "total_revenue": stats["revenue"],
                }
                for action, stats in actions.items()
            },
        }


def update_outcome_on_status_change(db: Session, claim: Claim):
    """
    Update outcome tracking when a claim status changes.
    
    Called after state transitions to automatically track outcomes.
    """
    # Find pending outcomes for this claim
    pending_outcomes = (
        db.query(OutcomeTracking)
        .filter(
            OutcomeTracking.claim_id == claim.id,
            OutcomeTracking.outcome == "PENDING",
        )
        .all()
    )
    
    for outcome in pending_outcomes:
        new_outcome = "PENDING"
        revenue_recovered = None
        
        if claim.status == ClaimStatus.PAID:
            new_outcome = "SUCCESS"
            revenue_recovered = float(claim.paid_amount or claim.amount)
        elif claim.status == ClaimStatus.WRITE_OFF:
            new_outcome = "FAILURE"
            revenue_recovered = 0.0
        elif claim.status in [ClaimStatus.DENIED, ClaimStatus.REJECTED]:
            # Check if this is a second denial after resubmission
            if outcome.action_taken == AgentDecisionEnum.RESUBMIT.value:
                new_outcome = "FAILURE"
            # Otherwise, might still be pending
        
        if new_outcome != "PENDING":
            outcome.outcome = new_outcome
            outcome.final_status = claim.status
            outcome.revenue_recovered = revenue_recovered
            outcome.outcome_date = datetime.utcnow()
            
            # Update success flags based on action
            if outcome.action_taken == AgentDecisionEnum.APPEAL.value:
                outcome.appeal_successful = "true" if new_outcome == "SUCCESS" else "false"
            elif outcome.action_taken == AgentDecisionEnum.RESUBMIT.value:
                outcome.resubmission_successful = "true" if new_outcome == "SUCCESS" else "false"
    
    db.commit()
