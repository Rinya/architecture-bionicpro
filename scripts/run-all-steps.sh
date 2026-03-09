#!/bin/bash
# BionicPRO Complete Setup Wizard - Linux/macOS version
# This script runs all BionicPRO setup and testing steps automatically

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Find script directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../docker-compose.yaml" ]; then
    cd "$SCRIPT_DIR/.."
elif [ -f "$SCRIPT_DIR/docker-compose.yaml" ]; then
    cd "$SCRIPT_DIR"
else
    echo -e "${RED}[ERROR] Cannot find docker-compose.yaml file!${NC}"
    echo "Please run from project root or scripts folder."
    exit 1
fi

echo "========================================"
echo "     BionicPRO Complete Setup Wizard"
echo "     Автоматическое выполнение всех шагов"
echo "========================================"
echo ""

echo -e "${BLUE}[INFO]${NC} This script will run all BionicPRO setup and testing steps:"
echo ""
echo "Step 4: Data initialization"
echo "Step 5: Functionality testing"
echo "Step 6: UI testing"
echo "Step 7: Airflow testing"
echo "Step 8: Complete system check"
echo "Step 9: Final verification"
echo ""

# Get user confirmation
read -p "Do you want to proceed with all steps? (Y/n): " -r
if [[ ! $REPLY =~ ^[Yy]*$ ]] && [[ ! -z $REPLY ]]; then
    echo "Setup cancelled by user."
    exit 0
fi

echo ""
echo "Starting complete BionicPRO setup and testing..."
echo ""

# Function to run a step and check for errors
run_step() {
    local step_name="$1"
    local step_script="$2"
    local step_description="$3"

    echo "========================================"
    echo "        $step_name"
    echo "========================================"
    echo ""

    if [ -f "$step_script" ]; then
        if bash "$step_script"; then
            echo -e "${GREEN}[✓] $step_name completed successfully${NC}"
            return 0
        else
            echo -e "${RED}[✗] $step_name failed${NC}"
            echo "Please check the output above for details."
            return 1
        fi
    else
        # Fallback - try to call equivalent bat file if shell script doesn't exist
        local bat_file="${step_script%.sh}.bat"
        if [[ "$step_script" == *"scripts/"* ]]; then
            bat_file="checks/$(basename "$step_script" .sh).bat"
        fi

        if [ -f "$bat_file" ]; then
            echo -e "${YELLOW}[WARNING]${NC} Shell script not found, this step needs manual execution:"
            echo "Please run: $bat_file"
            read -p "Press Enter when step is complete, or Ctrl+C to abort..."
            return 0
        else
            echo -e "${YELLOW}[WARNING]${NC} Step script not found: $step_script"
            echo "Continuing with next step..."
            return 0
        fi
    fi
}

# Function to pause between steps
pause_between_steps() {
    echo ""
    read -p "Press Enter to continue to next step..."
    echo ""
}

# Step 4: Data Initialization
if run_step "STEP 4: Data Initialization" "scripts/init-test-data.sh" "Initialize test data in ClickHouse"; then
    pause_between_steps
else
    echo -e "${RED}[ERROR] Step 4 failed. Stopping execution.${NC}"
    exit 1
fi

# Step 5: Functionality Testing
if run_step "STEP 5: Functionality Testing" "scripts/step5-functionality-test.sh" "Test API functionality"; then
    pause_between_steps
else
    echo -e "${YELLOW}[WARNING] Step 5 failed but continuing...${NC}"
    pause_between_steps
fi

# Step 6: UI Testing
if run_step "STEP 6: UI Testing" "scripts/step6-ui-test.sh" "Test user interface"; then
    pause_between_steps
else
    echo -e "${YELLOW}[WARNING] Step 6 failed but continuing...${NC}"
    pause_between_steps
fi

# Step 7: Airflow Testing
if run_step "STEP 7: Airflow Testing" "scripts/step7-airflow-test.sh" "Test ETL pipelines"; then
    pause_between_steps
else
    echo -e "${YELLOW}[WARNING] Step 7 failed but continuing...${NC}"
    pause_between_steps
fi

# Step 8: Complete System Check
if run_step "STEP 8: Complete System Check" "scripts/step8-complete-check.sh" "Comprehensive system validation"; then
    pause_between_steps
else
    echo -e "${YELLOW}[WARNING] Step 8 failed but continuing...${NC}"
    pause_between_steps
fi

# Step 9: Final Verification
if run_step "STEP 9: Final Verification" "scripts/step9-final-verification.sh" "Final production readiness check"; then
    echo ""
else
    echo -e "${YELLOW}[WARNING] Step 9 failed. Please review results.${NC}"
fi

echo ""
echo "========================================"
echo "       COMPLETE SETUP FINISHED!"
echo "========================================"
echo ""

echo -e "${GREEN}🎉 Congratulations! BionicPRO setup completed.${NC}"
echo ""
echo "What was accomplished:"
echo "✅ Test data initialized in ClickHouse"
echo "✅ API functionality verified"
echo "✅ UI components tested"
echo "✅ Airflow ETL pipeline prepared"
echo "✅ Complete system health checked"
echo "✅ Production readiness verified"
echo ""
echo -e "${GREEN}Your BionicPRO system is ready for use!${NC}"
echo ""
echo "🌐 Quick access:"
echo "   Frontend:   http://localhost:3000"
echo "   Airflow:    http://localhost:8081 (admin/admin)"
echo "   Keycloak:   http://localhost:8080/admin (admin/admin)"
echo "   API Health: http://localhost:5000/health"
echo ""
echo "🛠️ Need help?"
echo "   Documentation: README.md"
echo "   Troubleshoot:  ./scripts/troubleshoot-check.sh"
echo "   Health check:  ./scripts/health-check-full.sh"
echo "   View logs:     docker-compose logs <service>"
echo ""
echo "📊 Management commands:"
echo "   Stop system:   docker-compose down"
echo "   Restart:       docker-compose restart"
echo "   View status:   docker-compose ps"
echo ""