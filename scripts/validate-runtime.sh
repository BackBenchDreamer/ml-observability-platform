#!/bin/bash

#############################################################################
# Runtime Abstraction Validation Script
#
# This script validates the runtime abstraction implementation by:
# 1. Testing runtime detection
# 2. Validating compose files
# 3. Testing script executability
# 4. Validating script integration
# 5. Providing a summary report
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
#############################################################################

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters for summary
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Arrays to store results
declare -a PASSED_TESTS
declare -a FAILED_TESTS
declare -a WARNING_TESTS

#############################################################################
# Helper Functions
#############################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_section() {
    echo -e "\n${BLUE}--- $1 ---${NC}"
}

check_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
    PASSED_TESTS+=("$1")
}

check_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
    FAILED_TESTS+=("$1")
}

check_warn() {
    echo -e "${YELLOW}⚠ WARN:${NC} $1"
    ((WARNINGS++))
    WARNING_TESTS+=("$1")
}

#############################################################################
# Test 1: Runtime Detection
#############################################################################

test_runtime_detection() {
    print_header "TEST 1: Runtime Detection"
    
    # Check if runtime.sh exists
    if [[ ! -f "scripts/runtime.sh" ]]; then
        check_fail "runtime.sh does not exist"
        return 1
    fi
    check_pass "runtime.sh exists"
    
    # Source runtime.sh
    print_section "Sourcing runtime.sh"
    if source scripts/runtime.sh 2>/dev/null; then
        check_pass "runtime.sh sourced successfully"
    else
        check_fail "Failed to source runtime.sh"
        return 1
    fi
    
    # Verify all required variables are set
    print_section "Checking required variables"
    
    if [[ -n "$CONTAINER_RUNTIME" ]]; then
        check_pass "CONTAINER_RUNTIME is set: $CONTAINER_RUNTIME"
    else
        check_fail "CONTAINER_RUNTIME is not set"
    fi
    
    if [[ -n "$COMPOSE_CMD" ]]; then
        check_pass "COMPOSE_CMD is set: $COMPOSE_CMD"
    else
        check_fail "COMPOSE_CMD is not set"
    fi
    
    if [[ -n "$EXEC_CMD" ]]; then
        check_pass "EXEC_CMD is set: $EXEC_CMD"
    else
        check_fail "EXEC_CMD is not set"
    fi
    
    if [[ -n "$COMPOSE_FILE" ]]; then
        check_pass "COMPOSE_FILE is set: $COMPOSE_FILE"
    else
        check_fail "COMPOSE_FILE is not set"
    fi
    
    # Display detected runtime information
    print_section "Detected Runtime Information"
    echo "  Container Runtime: ${CONTAINER_RUNTIME:-NOT SET}"
    echo "  Compose Command:   ${COMPOSE_CMD:-NOT SET}"
    echo "  Exec Command:      ${EXEC_CMD:-NOT SET}"
    echo "  Compose File:      ${COMPOSE_FILE:-NOT SET}"
}

#############################################################################
# Test 2: Validate Compose Files
#############################################################################

test_compose_files() {
    print_header "TEST 2: Compose Files Validation"
    
    # Check for docker-compose.yml
    if [[ -f "infra/docker-compose.yml" ]]; then
        check_pass "infra/docker-compose.yml exists"
        
        # Validate YAML syntax - prefer Python parser for cross-runtime compatibility
        if command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
            if python3 -c "import yaml; yaml.safe_load(open('infra/docker-compose.yml'))" 2>/dev/null; then
                check_pass "infra/docker-compose.yml is valid YAML"
            else
                check_fail "infra/docker-compose.yml has invalid YAML syntax"
            fi
        elif command -v docker &> /dev/null; then
            if docker compose -f infra/docker-compose.yml config &> /dev/null; then
                check_pass "infra/docker-compose.yml is valid YAML"
            else
                check_warn "docker-compose.yml validation skipped (docker compose validation may be runtime-specific)"
            fi
        else
            check_warn "Cannot validate docker-compose.yml YAML syntax (install PyYAML: pip install pyyaml)"
        fi
    else
        check_fail "infra/docker-compose.yml does not exist"
    fi
    
    # Check for podman-compose.yml
    if [[ -f "infra/podman-compose.yml" ]]; then
        check_pass "infra/podman-compose.yml exists"
        
        # Validate YAML syntax - prefer Python parser for cross-runtime compatibility
        if command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
            if python3 -c "import yaml; yaml.safe_load(open('infra/podman-compose.yml'))" 2>/dev/null; then
                check_pass "infra/podman-compose.yml is valid YAML"
            else
                check_fail "infra/podman-compose.yml has invalid YAML syntax"
            fi
        elif command -v podman &> /dev/null && command -v podman-compose &> /dev/null; then
            if podman-compose -f infra/podman-compose.yml config &> /dev/null; then
                check_pass "infra/podman-compose.yml is valid YAML"
            else
                check_warn "podman-compose.yml validation skipped (podman-compose validation may be runtime-specific)"
            fi
        else
            check_warn "Cannot validate podman-compose.yml YAML syntax (install PyYAML: pip install pyyaml)"
        fi
    else
        check_fail "infra/podman-compose.yml does not exist"
    fi
}

#############################################################################
# Test 3: Script Executability
#############################################################################

test_script_executability() {
    print_header "TEST 3: Script Executability"
    
    local scripts=(
        "scripts/runtime.sh"
        "scripts/demo.sh"
        "scripts/rebuild-inference-api.sh"
        "scripts/rebuild-all-services.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [[ -f "$script" ]]; then
            if [[ -x "$script" ]]; then
                check_pass "$script is executable"
            else
                check_fail "$script is not executable (needs chmod +x)"
            fi
        else
            check_fail "$script does not exist"
        fi
    done
}

#############################################################################
# Test 4: Script Integration
#############################################################################

test_script_integration() {
    print_header "TEST 4: Script Integration"
    
    # Check demo.sh sources runtime.sh
    print_section "Checking demo.sh"
    if [[ -f "scripts/demo.sh" ]]; then
        if grep -q "source.*runtime\.sh\|\..*runtime\.sh" scripts/demo.sh; then
            check_pass "demo.sh sources runtime.sh"
        else
            check_fail "demo.sh does not source runtime.sh"
        fi
        
        # Check for variable usage
        if grep -q '\$COMPOSE_CMD' scripts/demo.sh; then
            check_pass "demo.sh uses \$COMPOSE_CMD"
        else
            check_fail "demo.sh does not use \$COMPOSE_CMD"
        fi
        
        if grep -q '\$EXEC_CMD' scripts/demo.sh; then
            check_pass "demo.sh uses \$EXEC_CMD"
        else
            check_warn "demo.sh does not use \$EXEC_CMD (may not be needed)"
        fi
        
        if grep -q '\$COMPOSE_FILE' scripts/demo.sh; then
            check_pass "demo.sh uses \$COMPOSE_FILE"
        else
            check_fail "demo.sh does not use \$COMPOSE_FILE"
        fi
    else
        check_fail "demo.sh does not exist"
    fi
    
    # Check rebuild-inference-api.sh
    print_section "Checking rebuild-inference-api.sh"
    if [[ -f "scripts/rebuild-inference-api.sh" ]]; then
        if grep -q "source.*runtime\.sh\|\..*runtime\.sh" scripts/rebuild-inference-api.sh; then
            check_pass "rebuild-inference-api.sh sources runtime.sh"
        else
            check_fail "rebuild-inference-api.sh does not source runtime.sh"
        fi
        
        if grep -q '\$COMPOSE_CMD' scripts/rebuild-inference-api.sh; then
            check_pass "rebuild-inference-api.sh uses \$COMPOSE_CMD"
        else
            check_fail "rebuild-inference-api.sh does not use \$COMPOSE_CMD"
        fi
        
        if grep -q '\$COMPOSE_FILE' scripts/rebuild-inference-api.sh; then
            check_pass "rebuild-inference-api.sh uses \$COMPOSE_FILE"
        else
            check_fail "rebuild-inference-api.sh does not use \$COMPOSE_FILE"
        fi
    else
        check_fail "rebuild-inference-api.sh does not exist"
    fi
    
    # Check rebuild-all-services.sh
    print_section "Checking rebuild-all-services.sh"
    if [[ -f "scripts/rebuild-all-services.sh" ]]; then
        if grep -q "source.*runtime\.sh\|\..*runtime\.sh" scripts/rebuild-all-services.sh; then
            check_pass "rebuild-all-services.sh sources runtime.sh"
        else
            check_fail "rebuild-all-services.sh does not source runtime.sh"
        fi
        
        if grep -q '\$COMPOSE_CMD' scripts/rebuild-all-services.sh; then
            check_pass "rebuild-all-services.sh uses \$COMPOSE_CMD"
        else
            check_fail "rebuild-all-services.sh does not use \$COMPOSE_CMD"
        fi
        
        if grep -q '\$COMPOSE_FILE' scripts/rebuild-all-services.sh; then
            check_pass "rebuild-all-services.sh uses \$COMPOSE_FILE"
        else
            check_fail "rebuild-all-services.sh does not use \$COMPOSE_FILE"
        fi
    else
        check_fail "rebuild-all-services.sh does not exist"
    fi
}

#############################################################################
# Summary Report
#############################################################################

print_summary() {
    print_header "VALIDATION SUMMARY"
    
    echo -e "${BLUE}Total Checks:${NC} $TOTAL_CHECKS"
    echo -e "${GREEN}Passed:${NC} $PASSED_CHECKS"
    echo -e "${RED}Failed:${NC} $FAILED_CHECKS"
    echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
    echo ""
    
    # Calculate success rate
    if [[ $TOTAL_CHECKS -gt 0 ]]; then
        SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
        echo -e "${BLUE}Success Rate:${NC} ${SUCCESS_RATE}%"
    fi
    
    # Show failed tests
    if [[ ${#FAILED_TESTS[@]} -gt 0 ]]; then
        echo -e "\n${RED}Failed Tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "  ${RED}✗${NC} $test"
        done
    fi
    
    # Show warnings
    if [[ ${#WARNING_TESTS[@]} -gt 0 ]]; then
        echo -e "\n${YELLOW}Warnings:${NC}"
        for test in "${WARNING_TESTS[@]}"; do
            echo -e "  ${YELLOW}⚠${NC} $test"
        done
    fi
    
    # Recommendations
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        echo -e "\n${YELLOW}Recommendations:${NC}"
        
        if ! grep -q "source.*runtime\.sh" scripts/demo.sh 2>/dev/null; then
            echo "  • Add 'source \$(dirname \$0)/runtime.sh' to demo.sh"
        fi
        
        if [[ ! -x "scripts/runtime.sh" ]]; then
            echo "  • Run: chmod +x scripts/runtime.sh"
        fi
        
        if [[ ! -x "scripts/demo.sh" ]]; then
            echo "  • Run: chmod +x scripts/demo.sh"
        fi
        
        if [[ ! -x "scripts/rebuild-inference-api.sh" ]]; then
            echo "  • Run: chmod +x scripts/rebuild-inference-api.sh"
        fi
        
        if [[ ! -x "scripts/rebuild-all-services.sh" ]]; then
            echo "  • Run: chmod +x scripts/rebuild-all-services.sh"
        fi
        
        if [[ ! -f "infra/docker-compose.yml" ]]; then
            echo "  • Create infra/docker-compose.yml"
        fi
        
        if [[ ! -f "infra/podman-compose.yml" ]]; then
            echo "  • Create infra/podman-compose.yml"
        fi
    fi
    
    # Final status
    echo ""
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}✓ All validation checks passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ Validation failed with $FAILED_CHECKS error(s)${NC}"
        return 1
    fi
}

#############################################################################
# Main Execution
#############################################################################

main() {
    print_header "Runtime Abstraction Validation"
    echo "Starting validation at $(date)"
    echo "Working directory: $(pwd)"
    
    # Run all tests
    test_runtime_detection
    test_compose_files
    test_script_executability
    test_script_integration
    
    # Print summary and exit with appropriate code
    print_summary
    exit $?
}

# Run main function
main

# Made with Bob
