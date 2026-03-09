#!/bin/bash
# BionicPRO Quick Health Check - Linux/macOS version
# This script performs a quick health check of all BionicPRO services

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
echo "     BionicPRO Quick Health Check"
echo "========================================"
echo ""

echo "Testing all endpoints..."
echo ""

# Define endpoints to test
endpoints=(
    "Frontend;http://localhost:3000"
    "Keycloak;http://localhost:8080/realms/reports-realm"
    "Airflow;http://localhost:8081/health"
    "Reports API;http://localhost:5000/health"
    "ClickHouse;http://localhost:8123/ping"
)

success_count=0
total_count=${#endpoints[@]}

# Test each endpoint
for endpoint in "${endpoints[@]}"; do
    IFS=';' read -r name url <<< "$endpoint"
    echo "Testing $name..."

    if curl -s --max-time 5 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}[✓]${NC} $name - OK"
        ((success_count++))
    else
        echo -e "${RED}[✗]${NC} $name - FAILED ($url)"
    fi
    echo ""
done

echo "========================================"
echo "Container Status Summary:"
echo "========================================"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "========================================"
echo "           Summary"
echo "========================================"
failed_count=$((total_count - success_count))
echo "Services tested: $total_count"
echo "Services OK: $success_count"
echo "Services FAILED: $failed_count"

if [ $success_count -eq $total_count ]; then
    echo ""
    echo -e "${GREEN}[✓] ALL SYSTEMS OPERATIONAL${NC}"
    echo "System is ready to use!"
else
    echo ""
    echo -e "${YELLOW}[!] SOME SERVICES FAILED${NC}"
    echo "Check the detailed output above."
    echo "Run './scripts/health-check-full.sh' for detailed diagnostics."
fi

echo ""
echo "Quick access URLs:"
echo "- Frontend:    http://localhost:3000"
echo "- Airflow UI:  http://localhost:8081"
echo "- Keycloak:    http://localhost:8080/admin"
echo ""