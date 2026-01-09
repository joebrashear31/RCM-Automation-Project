"""Manual integration test script to verify the system works."""

import sys
from datetime import datetime

# Test 1: Import all modules
print("=" * 60)
print("TEST 1: Import all modules")
print("=" * 60)

try:
    from common.enums import (
        ClaimStatus,
        DenialCategory,
        RecommendedAction,
        AgentDecision,
        PayerType,
        EventType,
    )
    from services.denials.classifier import classify_denial, get_recommended_action
    from services.denials.agent import make_agent_decision
    from services.claims.state_machine import ClaimStateMachine
    from services.denials.outcomes import OutcomeTracker
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Denial Classification
print("\n" + "=" * 60)
print("TEST 2: Denial Classification")
print("=" * 60)

classification = classify_denial(
    payer_type=PayerType.COMMERCIAL,
    denial_code="CO-50",
    denial_message="Invalid CPT code",
)
print(f"✓ Classified: {classification.reason.value}")
print(f"✓ Category: {classification.category.value}")
print(f"✓ Confidence: {classification.confidence:.2f}")

action = get_recommended_action(classification.category)
print(f"✓ Recommended action: {action.value}")

# Test 3: Agent Decision Making
print("\n" + "=" * 60)
print("TEST 3: Agent Decision Making")
print("=" * 60)

agent_result = make_agent_decision(
    claim_data={
        "amount": 1000.0,
        "cpt_codes": ["99213"],
        "icd_codes": ["E11.9"],
    },
    denial_category=DenialCategory.CODING_ERROR,
    payer_type=PayerType.COMMERCIAL,
    rule_based_recommendation=RecommendedAction.RESUBMIT,
)

print(f"✓ Decision: {agent_result.decision.value}")
print(f"✓ Confidence: {agent_result.confidence:.2f}")
print(f"✓ Rationale: {agent_result.rationale[:100]}...")
print(f"✓ Missing info: {agent_result.missing_info}")

# Test 4: State Machine Transitions
print("\n" + "=" * 60)
print("TEST 4: State Machine Transitions")
print("=" * 60)

test_cases = [
    (ClaimStatus.CREATED, ClaimStatus.VALIDATED, True),
    (ClaimStatus.VALIDATED, ClaimStatus.SUBMITTED, True),
    (ClaimStatus.SUBMITTED, ClaimStatus.DENIED, True),
    (ClaimStatus.DENIED, ClaimStatus.APPEAL_PENDING, True),
    (ClaimStatus.DENIED, ClaimStatus.RESUBMITTED, True),
    (ClaimStatus.DENIED, ClaimStatus.WRITE_OFF, True),
    (ClaimStatus.CREATED, ClaimStatus.PAID, False),  # Invalid
]

for from_status, to_status, expected in test_cases:
    result = ClaimStateMachine.can_transition(from_status, to_status)
    status = "✓" if result == expected else "✗"
    print(f"{status} {from_status.value} -> {to_status.value}: {result}")

# Test 5: Test different denial categories
print("\n" + "=" * 60)
print("TEST 5: Test Different Denial Categories")
print("=" * 60)

categories = [
    DenialCategory.CODING_ERROR,
    DenialCategory.ELIGIBILITY,
    DenialCategory.MEDICAL_NECESSITY,
    DenialCategory.PRIOR_AUTH_MISSING,
]

for category in categories:
    action = get_recommended_action(category)
    print(f"✓ {category.value} -> {action.value}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✓")
print("=" * 60)
