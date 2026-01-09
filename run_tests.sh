#!/bin/bash
# Test runner script for RCM Workflow Engine

set -e

echo "🧪 RCM Workflow Engine Test Suite"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing dependencies..."
    pip install -r requirements.txt
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"
VERBOSE="${2:-}"

case "$TEST_TYPE" in
    unit)
        echo -e "${BLUE}Running unit tests...${NC}"
        pytest tests/unit/ $VERBOSE
        ;;
    integration)
        echo -e "${BLUE}Running integration tests...${NC}"
        pytest tests/integration/ $VERBOSE
        ;;
    state-machine)
        echo -e "${BLUE}Running state machine tests...${NC}"
        pytest tests/unit/test_state_machine.py $VERBOSE
        ;;
    validator)
        echo -e "${BLUE}Running validator tests...${NC}"
        pytest tests/unit/test_validator.py $VERBOSE
        ;;
    classifier)
        echo -e "${BLUE}Running classifier tests...${NC}"
        pytest tests/unit/test_classifier.py $VERBOSE
        ;;
    api)
        echo -e "${BLUE}Running API route tests...${NC}"
        pytest tests/integration/test_api_routes.py $VERBOSE
        ;;
    celery)
        echo -e "${BLUE}Running Celery task tests...${NC}"
        pytest tests/integration/test_celery_tasks.py $VERBOSE
        ;;
    coverage)
        echo -e "${BLUE}Running all tests with coverage...${NC}"
        pytest --cov=. --cov-report=term-missing --cov-report=html
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    all|*)
        echo -e "${BLUE}Running all tests...${NC}"
        pytest tests/ $VERBOSE
        ;;
esac

echo ""
echo -e "${GREEN}✅ Tests completed!${NC}"
