#!/bin/bash
# BionicPRO Troubleshoot Checker - Linux/macOS version
# This script performs comprehensive system diagnostics

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
echo "    BionicPRO Troubleshoot Checker"
echo "========================================"
echo ""

echo "========================================"
echo "    Port Availability Check"
echo "========================================"
echo ""

ports=(3000 5000 5433 5434 6380 8080 8081 8123 9000 9092)

echo "Checking if required ports are free..."
for port in "${ports[@]}"; do
    if command -v lsof > /dev/null 2>&1; then
        # macOS and most Linux distributions with lsof
        if lsof -i ":$port" > /dev/null 2>&1; then
            echo -e "${YELLOW}[!]${NC} Port $port is occupied"
            lsof -i ":$port"
        else
            echo -e "${GREEN}[✓]${NC} Port $port is free"
        fi
    elif command -v ss > /dev/null 2>&1; then
        # Modern Linux with ss command
        if ss -ln | grep ":$port " > /dev/null; then
            echo -e "${YELLOW}[!]${NC} Port $port is occupied"
            ss -ln | grep ":$port "
        else
            echo -e "${GREEN}[✓]${NC} Port $port is free"
        fi
    else
        # Fallback to netstat
        if netstat -ln 2>/dev/null | grep ":$port " > /dev/null; then
            echo -e "${YELLOW}[!]${NC} Port $port is occupied"
            netstat -ln | grep ":$port "
        else
            echo -e "${GREEN}[✓]${NC} Port $port is free"
        fi
    fi
done

echo ""
echo "========================================"
echo "    Memory and Disk Space Check"
echo "========================================"
echo ""

echo "Available memory:"
if command -v free > /dev/null 2>&1; then
    # Linux
    free -h
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Physical Memory:"
    echo "  Total: $(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))GB"
    echo "  Available: $(( $(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.') * 4096 / 1024 / 1024 ))MB"
fi

echo ""
echo "Disk space for Docker:"
docker system df

echo ""
echo "========================================"
echo "    Docker Network Check"
echo "========================================"
echo ""

echo "Checking Docker networks..."
if docker network ls | grep bionicpro > /dev/null; then
    echo -e "${GREEN}[✓]${NC} BionicPRO networks exist"
    docker network ls | grep bionicpro
else
    echo -e "${YELLOW}[!]${NC} BionicPRO networks not found"
    echo "Available networks:"
    docker network ls
fi

echo ""
echo "========================================"
echo "    Environment Variables Check"
echo "========================================"
echo ""

if [ -f .env ]; then
    echo -e "${GREEN}[✓]${NC} .env file exists"
    echo "Checking critical variables..."

    check_var() {
        local var_name="$1"
        if grep "^$var_name=" .env > /dev/null 2>&1; then
            echo -e "${GREEN}[✓]${NC} $var_name is set"
        else
            echo -e "${RED}[!]${NC} $var_name is missing"
        fi
    }

    check_var "JWT_SECRET_KEY"
    check_var "POSTGRES_KEYCLOAK_PASSWORD"
    check_var "POSTGRES_AIRFLOW_PASSWORD"
    check_var "CLICKHOUSE_PASSWORD"
    check_var "REDIS_PASSWORD"

    if grep "^AIRFLOW_UID=" .env > /dev/null 2>&1; then
        echo -e "${GREEN}[✓]${NC} AIRFLOW_UID is set"
    else
        echo -e "${RED}[!]${NC} AIRFLOW_UID is missing - this will cause startup issues"
    fi

else
    echo -e "${RED}[✗]${NC} .env file not found!"
    echo "Please copy .env.example to .env and configure it."
fi

echo ""
echo "========================================"
echo "    Container Health Details"
echo "========================================"
echo ""

echo "Checking container statuses..."
docker-compose ps

echo ""
echo "Unhealthy containers:"
if docker-compose ps | grep -E "unhealthy|Exit"; then
    echo "Found issues with containers above"
else
    echo -e "${GREEN}No unhealthy containers found${NC}"
fi

echo ""
echo "Recent container events (last 10 minutes):"
docker events --since 10m --until 0s 2>/dev/null || echo "No recent events"

echo ""
echo "========================================"
echo "    Volume and Permission Check"
echo "========================================"
echo ""

echo "Docker volumes:"
docker volume ls | grep bionicpro || echo "No BionicPRO volumes found"

echo ""

# Check and create required directories
for dir in logs dags plugins; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}[✓]${NC} $dir directory exists"
    else
        echo -e "${YELLOW}[!]${NC} $dir directory missing"
        mkdir -p "$dir"
        echo -e "${GREEN}[✓]${NC} $dir directory created"
    fi
done

echo ""
echo "========================================"
echo "    Quick Fix Suggestions"
echo "========================================"
echo ""

echo "Common fixes:"
echo "1. If ports are occupied: Stop conflicting services"
echo "2. If memory issues: docker system prune -a"
echo "3. If network issues: docker network create bionicpro-network"
echo "4. If AIRFLOW_UID missing: echo 'AIRFLOW_UID=50000' >> .env"
echo "5. If containers unhealthy: docker-compose restart <service>"
echo ""

echo "For detailed logs of a specific service:"
echo "   docker-compose logs <service-name>"
echo ""
echo "For complete restart:"
echo "   docker-compose down && docker-compose up -d"
echo ""

# Check if running on macOS and suggest Docker Desktop settings
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS specific tips:"
    echo "- Ensure Docker Desktop has sufficient memory allocated (8GB+)"
    echo "- Check Docker Desktop → Preferences → Resources → Memory"
    echo ""
fi

# Check if running on Linux and suggest systemd commands
if [[ "$OSTYPE" == "linux"* ]]; then
    echo "Linux specific tips:"
    echo "- Check systemd services that might conflict:"
    echo "  sudo systemctl status apache2 nginx"
    echo "- Ensure user is in docker group:"
    echo "  sudo usermod -aG docker \$USER && newgrp docker"
    echo ""
fi