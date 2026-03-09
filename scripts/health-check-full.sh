#!/bin/bash
# BionicPRO Full Health Check - Linux/macOS version
# This script performs comprehensive health check of all system components

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
echo "     BionicPRO Full Health Check"
echo "========================================"
echo ""

# Function to test HTTP endpoint
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"

    echo -n "Testing $name... "

    if command -v curl > /dev/null 2>&1; then
        response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
        if [ "$response_code" = "$expected_code" ]; then
            echo -e "${GREEN}[✓] OK${NC} (HTTP $response_code)"
            return 0
        else
            echo -e "${RED}[✗] FAILED${NC} (HTTP $response_code, expected $expected_code)"
            return 1
        fi
    else
        echo -e "${YELLOW}[?] SKIPPED${NC} (curl not available)"
        return 1
    fi
}

# Function to test TCP connection
test_tcp_connection() {
    local name="$1"
    local host="$2"
    local port="$3"

    echo -n "Testing $name TCP connection... "

    if command -v nc > /dev/null 2>&1; then
        if nc -z "$host" "$port" 2>/dev/null; then
            echo -e "${GREEN}[✓] OK${NC}"
            return 0
        else
            echo -e "${RED}[✗] FAILED${NC}"
            return 1
        fi
    elif command -v telnet > /dev/null 2>&1; then
        if timeout 5 telnet "$host" "$port" </dev/null >/dev/null 2>&1; then
            echo -e "${GREEN}[✓] OK${NC}"
            return 0
        else
            echo -e "${RED}[✗] FAILED${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}[?] SKIPPED${NC} (nc/telnet not available)"
        return 1
    fi
}

total_checks=0
passed_checks=0

echo "========================================"
echo "    Core Services HTTP Endpoints"
echo "========================================"
echo ""

# Core HTTP endpoints
endpoints=(
    "Frontend;http://localhost:3000;200"
    "Keycloak Realm;http://localhost:8080/realms/reports-realm;200"
    "Keycloak Admin;http://localhost:8080/admin;200"
    "Airflow Health;http://localhost:8081/health;200"
    "Reports API Health;http://localhost:5000/health;200"
    "ClickHouse Ping;http://localhost:8123/ping;200"
)

for endpoint in "${endpoints[@]}"; do
    IFS=';' read -r name url expected_code <<< "$endpoint"
    ((total_checks++))
    if test_endpoint "$name" "$url" "$expected_code"; then
        ((passed_checks++))
    fi
done

echo ""
echo "========================================"
echo "    Database TCP Connections"
echo "========================================"
echo ""

# Database connections
databases=(
    "PostgreSQL Keycloak;localhost;5433"
    "PostgreSQL Airflow;localhost;5434"
    "ClickHouse HTTP;localhost;8123"
    "ClickHouse Native;localhost;9000"
    "Redis;localhost;6380"
    "Kafka;localhost;9092"
)

for database in "${databases[@]}"; do
    IFS=';' read -r name host port <<< "$database"
    ((total_checks++))
    if test_tcp_connection "$name" "$host" "$port"; then
        ((passed_checks++))
    fi
done

echo ""
echo "========================================"
echo "    Container Health Status"
echo "========================================"
echo ""

echo "Container statuses:"
docker-compose ps

echo ""
echo "Health check details:"
((total_checks++))
if docker-compose ps | grep -E "unhealthy|Exit" > /dev/null; then
    echo -e "${RED}[✗]${NC} Some containers are unhealthy or stopped"
    echo "Problematic containers:"
    docker-compose ps | grep -E "unhealthy|Exit" || true
else
    echo -e "${GREEN}[✓]${NC} All containers are healthy"
    ((passed_checks++))
fi

echo ""
echo "========================================"
echo "    Authentication Flow Test"
echo "========================================"
echo ""

echo -n "Testing Keycloak authentication endpoint... "
((total_checks++))
if test_endpoint "Keycloak Auth" "http://localhost:8080/realms/reports-realm/protocol/openid-connect/token" "405"; then
    ((passed_checks++))
fi

echo ""
echo "========================================"
echo "    Data Pipeline Readiness"
echo "========================================"
echo ""

echo -n "Checking Airflow scheduler... "
((total_checks++))
if docker-compose ps | grep "airflow-scheduler" | grep "Up" > /dev/null; then
    echo -e "${GREEN}[✓] Running${NC}"
    ((passed_checks++))
else
    echo -e "${RED}[✗] Not running${NC}"
fi

echo -n "Checking Airflow webserver... "
((total_checks++))
if docker-compose ps | grep "airflow-webserver" | grep "Up" > /dev/null; then
    echo -e "${GREEN}[✓] Running${NC}"
    ((passed_checks++))
else
    echo -e "${RED}[✗] Not running${NC}"
fi

echo ""
echo "========================================"
echo "    Security Configuration"
echo "========================================"
echo ""

((total_checks++))
if [ -f .env ]; then
    echo -e "${GREEN}[✓]${NC} Environment file exists"
    ((passed_checks++))

    # Check critical security variables
    security_vars=("JWT_SECRET_KEY" "POSTGRES_KEYCLOAK_PASSWORD" "POSTGRES_AIRFLOW_PASSWORD" "CLICKHOUSE_PASSWORD" "REDIS_PASSWORD")

    for var in "${security_vars[@]}"; do
        ((total_checks++))
        if grep -q "^${var}=" .env && ! grep -q "^${var}=.*your.*here" .env; then
            echo -e "${GREEN}[✓]${NC} $var is properly configured"
            ((passed_checks++))
        else
            echo -e "${RED}[✗]${NC} $var is not properly configured"
        fi
    done
else
    echo -e "${RED}[✗]${NC} Environment file missing"
fi

echo ""
echo "========================================"
echo "    Resource Usage"
echo "========================================"
echo ""

echo "Docker system information:"
docker system df

echo ""
echo "Container resource usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

echo ""
echo "========================================"
echo "    Network Configuration"
echo "========================================"
echo ""

((total_checks++))
if docker network ls | grep bionicpro > /dev/null; then
    echo -e "${GREEN}[✓]${NC} BionicPRO network exists"
    ((passed_checks++))
    echo "Network details:"
    docker network inspect bionicpro-network 2>/dev/null | grep -E "(Name|Driver|Subnet)" || echo "Network details not available"
else
    echo -e "${RED}[✗]${NC} BionicPRO network missing"
fi

echo ""
echo "========================================"
echo "    Log Analysis"
echo "========================================"
echo ""

echo "Recent errors in logs (last 50 lines):"
services=("frontend" "reports-api" "keycloak" "airflow-webserver" "airflow-scheduler" "clickhouse")

for service in "${services[@]}"; do
    echo ""
    echo "--- $service errors ---"
    if docker-compose logs --tail=50 "$service" 2>/dev/null | grep -i -E "(error|exception|failed|fatal)" | head -5; then
        true
    else
        echo "No recent errors found"
    fi
done

echo ""
echo "========================================"
echo "           Final Summary"
echo "========================================"
echo ""

failed_checks=$((total_checks - passed_checks))
success_rate=$((passed_checks * 100 / total_checks))

echo "Health Check Results:"
echo "===================="
echo "Total checks: $total_checks"
echo "Passed: $passed_checks"
echo "Failed: $failed_checks"
echo "Success rate: $success_rate%"
echo ""

if [ $success_rate -ge 90 ]; then
    echo -e "${GREEN}🟢 SYSTEM HEALTH: EXCELLENT${NC}"
    echo "System is ready for production use."
elif [ $success_rate -ge 75 ]; then
    echo -e "${YELLOW}🟡 SYSTEM HEALTH: GOOD${NC}"
    echo "System is operational but some issues need attention."
elif [ $success_rate -ge 50 ]; then
    echo -e "${YELLOW}🟠 SYSTEM HEALTH: FAIR${NC}"
    echo "System has significant issues that should be resolved."
else
    echo -e "${RED}🔴 SYSTEM HEALTH: POOR${NC}"
    echo "System has critical issues and is not ready for use."
fi

echo ""
echo "Next steps:"
if [ $success_rate -lt 100 ]; then
    echo "1. Review failed checks above"
    echo "2. Run './scripts/troubleshoot-check.sh' for detailed diagnostics"
    echo "3. Check service logs with: docker-compose logs <service-name>"
fi

echo "4. For complete system initialization: './scripts/run-all-steps.sh'"
echo "5. Access points:"
echo "   - Frontend: http://localhost:3000"
echo "   - Airflow: http://localhost:8081 (admin/admin)"
echo "   - Keycloak Admin: http://localhost:8080/admin (admin/admin)"
echo ""

# Set exit code based on success rate
if [ $success_rate -lt 75 ]; then
    exit 1
else
    exit 0
fi