"""Celery tasks for async claim processing."""

from common.celery_app import celery_app
from services.claims import models
from services.rules import validator
from services.denials import classifier
from common.db import SessionLocal
from common.enums import ClaimStatus
from services.claims import state_machine
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="validate_claim_rules")
def validate_claim_rules_task(claim_id: int):
    """
    Async task to validate a claim against payer rules.

    Transitions claim from CREATED -> VALIDATED if rules pass.
    """
    db = SessionLocal()
    try:
        claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
        if not claim:
            logger.error(f"Claim {claim_id} not found")
            return {"status": "error", "message": "Claim not found"}

        if claim.status != ClaimStatus.CREATED.value:
            logger.warning(f"Claim {claim_id} is not in CREATED state, skipping validation")
            return {"status": "skipped", "message": f"Claim is in {claim.status} state"}

        # Run validation
        validation_result = validator.validate_claim(claim)

        if validation_result.is_valid:
            # Transition to VALIDATED
            state_machine.ClaimStateMachine.transition(
                db=db,
                claim=claim,
                target_status=ClaimStatus.VALIDATED,
                reason="Payer rule validation passed",
            )
            logger.info(f"Claim {claim_id} validated successfully")
            return {
                "status": "success",
                "claim_id": claim_id,
                "warnings": validation_result.warnings,
            }
        else:
            logger.warning(
                f"Claim {claim_id} validation failed: {', '.join(validation_result.errors)}"
            )
            return {
                "status": "failed",
                "claim_id": claim_id,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
            }

    except Exception as e:
        logger.error(f"Error validating claim {claim_id}: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="classify_denial")
def classify_denial_task(claim_id: int, denial_code: str, denial_message: str):
    """
    Async task to classify a denial reason and update claim.

    Called when a claim is denied by the payer.
    """
    db = SessionLocal()
    try:
        claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
        if not claim:
            logger.error(f"Claim {claim_id} not found")
            return {"status": "error", "message": "Claim not found"}

        # Classify the denial
        classification = classifier.classify_denial(
            payer_type=claim.payer_type,
            denial_code=denial_code,
            denial_message=denial_message,
            claim_data={
                "cpt_codes": claim.cpt_codes,
                "icd_codes": claim.icd_codes,
                "amount": float(claim.amount),
            },
        )

        # Update claim with denial information
        claim.denial_reason = classification.reason.value
        claim.denial_details = classification.details

        db.commit()
        logger.info(
            f"Claim {claim_id} denial classified as {classification.reason.value}"
        )
        return {
            "status": "success",
            "claim_id": claim_id,
            "denial_reason": classification.reason.value,
            "confidence": classification.confidence,
        }

    except Exception as e:
        logger.error(f"Error classifying denial for claim {claim_id}: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

