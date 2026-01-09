"""Verify code structure and logic without requiring all dependencies."""

import ast
import os

print("=" * 60)
print("CODE VERIFICATION - Syntax and Structure Check")
print("=" * 60)

# Check Python syntax
files_to_check = [
    "common/enums.py",
    "services/denials/classifier.py",
    "services/denials/agent.py",
    "services/denials/orchestrator.py",
    "services/denials/outcomes.py",
    "services/claims/state_machine.py",
]

print("\n1. Checking Python syntax...")
for file_path in files_to_check:
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                ast.parse(f.read())
            print(f"  ✓ {file_path}")
        except SyntaxError as e:
            print(f"  ✗ {file_path}: {e}")
    else:
        print(f"  ✗ {file_path}: File not found")

# Check that enums are defined correctly
print("\n2. Checking enum definitions...")
try:
    with open("common/enums.py", 'r') as f:
        content = f.read()
        required_enums = [
            "DenialCategory",
            "RecommendedAction",
            "AgentDecision",
            "EventType",
            "ClaimStatus",
        ]
        for enum in required_enums:
            if f"class {enum}" in content:
                print(f"  ✓ {enum} enum defined")
            else:
                print(f"  ✗ {enum} enum missing")
except Exception as e:
    print(f"  ✗ Error checking enums: {e}")

# Check that key functions exist
print("\n3. Checking key functions...")
functions_to_check = {
    "services/denials/classifier.py": ["classify_denial", "get_recommended_action"],
    "services/denials/agent.py": ["make_agent_decision"],
    "services/denials/orchestrator.py": ["process_denial", "execute_agent_decision"],
    "services/denials/outcomes.py": ["record_outcome", "get_success_rate"],
}

for file_path, functions in functions_to_check.items():
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
            for func in functions:
                if f"def {func}" in content or f"class {func.split('_')[0].title()}" in content:
                    print(f"  ✓ {file_path}: {func}")
                else:
                    print(f"  ✗ {file_path}: {func} missing")

# Check models
print("\n4. Checking database models...")
try:
    with open("services/claims/models.py", 'r') as f:
        content = f.read()
        required_models = [
            "ClaimEvent",
            "DenialEvent",
            "AgentDecision",
            "OutcomeTracking",
        ]
        for model in required_models:
            if f"class {model}" in content:
                print(f"  ✓ {model} model defined")
            else:
                print(f"  ✗ {model} model missing")
except Exception as e:
    print(f"  ✗ Error checking models: {e}")

# Check routes
print("\n5. Checking API routes...")
try:
    with open("services/claims/routes.py", 'r') as f:
        content = f.read()
        required_routes = [
            "get_claim_events",
            "get_claim_denials",
            "create_denial_event",
            "process_denial",
            "get_agent_decisions",
            "execute_agent_decision",
            "human_override_decision",
        ]
        for route in required_routes:
            if f"def {route}" in content:
                print(f"  ✓ Route function: {route}")
            else:
                print(f"  ✗ Route function missing: {route}")
except Exception as e:
    print(f"  ✗ Error checking routes: {e}")

print("\n" + "=" * 60)
print("Verification complete!")
print("=" * 60)
