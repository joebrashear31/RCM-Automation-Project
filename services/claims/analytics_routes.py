"""Analytics routes for outcome tracking and learning loop."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from common.db import get_db
from common.enums import DenialCategory, AgentDecision as AgentDecisionEnum

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/success-rates")
def get_success_rates(
    denial_category: Optional[DenialCategory] = None,
    action_taken: Optional[AgentDecisionEnum] = None,
    days_back: int = 90,
    db: Session = Depends(get_db),
):
    """Get historical success rates for denial resolution actions."""
    from services.denials.outcomes import OutcomeTracker
    
    success_rate = OutcomeTracker.get_success_rate(
        db=db,
        denial_category=denial_category,
        action_taken=action_taken,
        days_back=days_back,
    )
    
    return {
        "denial_category": denial_category.value if denial_category else None,
        "action_taken": action_taken.value if action_taken else None,
        "days_back": days_back,
        "success_rate": success_rate,
        "has_data": success_rate is not None,
    }


@router.get("/revenue-metrics")
def get_revenue_metrics(
    days_back: int = 90,
    db: Session = Depends(get_db),
):
    """Get revenue recovery metrics."""
    from services.denials.outcomes import OutcomeTracker
    
    metrics = OutcomeTracker.get_revenue_metrics(db=db, days_back=days_back)
    
    return metrics


@router.get("/learning-insights/{denial_category}")
def get_learning_insights(
    denial_category: DenialCategory,
    days_back: int = 90,
    db: Session = Depends(get_db),
):
    """Get learning insights for a specific denial category."""
    from services.denials.outcomes import OutcomeTracker
    
    insights = OutcomeTracker.get_learning_insights(
        db=db,
        denial_category=denial_category,
        days_back=days_back,
    )
    
    return insights
