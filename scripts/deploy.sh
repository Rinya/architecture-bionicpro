#!/bin/bash
# BionicPRO Deployment Script - Linux/macOS version
# This script handles the complete deployment of BionicPRO system

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
REBUILD=false
PULL=false
DETACHED=true
CLEAN=false

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -r, --rebuild     Rebuild all images before starting"
    echo "  -p, --pull        Pull latest images before starting"
    echo "  -f, --foreground  Run in foreground (not detached)"
    echo "  -c, --clean       Clean system (remove volumes and networks) before deploy"
    echo "  -h, --help        Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0                Deploy with default settings"
    echo "  $0 --rebuild      Rebuild and deploy"
    echo "  $0 --clean        Clean deploy (removes all data)"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--rebuild)
            REBUILD=true
            shift
            ;;
        -p|--pull)
            PULL=true
            shift
            ;;
        -f|--foreground)
            DETACHED=false
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

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
echo "        BionicPRO Deployment"
echo "========================================"
echo ""

# Pre-flight checks
echo -e "${BLUE}[INFO]${NC} Performing pre-flight checks..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] Docker is not running!${NC}"
    echo "Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] docker-compose is not installed!${NC}"
    echo "Please install docker-compose and try again."
    exit 1
fi

# Check .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}[WARNING] .env file not found!${NC}"
    if [ -f .env.example ]; then
        echo "Copying .env.example to .env..."
        cp .env.example .env
        echo -e "${YELLOW}[WARNING] Please edit .env file with your configuration before continuing!${NC}"
        read -p "Press Enter to continue or Ctrl+C to abort..."
    else
        echo -e "${RED}[ERROR] No .env.example file found!${NC}"
        exit 1
    fi
fi

# Clean deployment if requested
if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}[WARNING] Clean deployment requested!${NC}"
    echo "This will remove all containers, volumes, and networks."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}[INFO]${NC} Cleaning up existing deployment..."
        docker-compose down -v --remove-orphans 2>/dev/null || true
        docker volume prune -f 2>/dev/null || true
        docker network prune -f 2>/dev/null || true
        echo -e "${GREEN}[✓]${NC} Cleanup completed"
    else
        echo "Cleanup cancelled."
        exit 0
    fi
fi

# Pull images if requested
if [ "$PULL" = true ]; then
    echo -e "${BLUE}[INFO]${NC} Pulling latest images..."
    docker-compose pull
    echo -e "${GREEN}[✓]${NC} Images pulled"
fi

# Stop existing containers
echo -e "${BLUE}[INFO]${NC} Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build or rebuild images
if [ "$REBUILD" = true ]; then
    echo -e "${BLUE}[INFO]${NC} Rebuilding all images..."
    docker-compose build --no-cache
    echo -e "${GREEN}[✓]${NC} Images rebuilt"
else
    echo -e "${BLUE}[INFO]${NC} Building images (if needed)..."
    docker-compose build
    echo -e "${GREEN}[✓]${NC} Images ready"
fi

# Create required directories
echo -e "${BLUE}[INFO]${NC} Creating required directories..."
mkdir -p logs dags plugins sql
echo -e "${GREEN}[✓]${NC} Directories created"

# Set proper permissions for Airflow
echo -e "${BLUE}[INFO]${NC} Setting Airflow permissions..."
if [ -z "$AIRFLOW_UID" ]; then
    if grep -q "^AIRFLOW_UID=" .env; then
        export AIRFLOW_UID=$(grep "^AIRFLOW_UID=" .env | cut -d '=' -f2)
    else
        export AIRFLOW_UID=50000
        echo "AIRFLOW_UID=$AIRFLOW_UID" >> .env
    fi
fi

# Fix directory permissions
if [[ "$OSTYPE" != "darwin"* ]]; then
    # Only set ownership on Linux, not macOS
    sudo chown -R "$AIRFLOW_UID:0" logs dags plugins 2>/dev/null || {
        echo -e "${YELLOW}[WARNING]${NC} Could not set ownership for Airflow directories"
        echo "You may need to run: sudo chown -R $AIRFLOW_UID:0 logs dags plugins"
    }
fi

echo -e "${GREEN}[✓]${NC} Permissions configured"

# Start services
echo -e "${BLUE}[INFO]${NC} Starting BionicPRO services..."

if [ "$DETACHED" = true ]; then
    docker-compose up -d
    echo -e "${GREEN}[✓]${NC} Services started in background"

    # Wait for services to be ready
    echo -e "${BLUE}[INFO]${NC} Waiting for services to be ready..."
    sleep 10

    # Quick health check
    echo -e "${BLUE}[INFO]${NC} Performing quick health check..."

    # Check if health check script exists
    if [ -f "scripts/quick-health-check.sh" ]; then
        bash scripts/quick-health-check.sh
    else
        # Fallback simple check
        echo "Checking core services..."
        services_ready=0
        total_services=5

        endpoints=(
            "Frontend:http://localhost:3000"
            "Keycloak:http://localhost:8080/realms/reports-realm"
            "Airflow:http://localhost:8081/health"
            "API:http://localhost:5000/health"
            "ClickHouse:http://localhost:8123/ping"
        )

        for endpoint in "${endpoints[@]}"; do
            IFS=':' read -r name url <<< "$endpoint"
            if curl -s --max-time 5 "$url" >/dev/null 2>&1; then
                echo -e "${GREEN}[✓]${NC} $name is ready"
                ((services_ready++))
            else
                echo -e "${RED}[✗]${NC} $name is not ready"
            fi
        done

        echo ""
        echo "Services ready: $services_ready/$total_services"
    fi

else
    echo "Starting in foreground mode (use Ctrl+C to stop)..."
    docker-compose up
fi

# Display final information
echo ""
echo "========================================"
echo "        Deployment Complete!"
echo "========================================"
echo ""

if [ "$DETACHED" = true ]; then
    echo -e "${GREEN}✅ BionicPRO has been deployed successfully!${NC}"
    echo ""
    echo "🌐 Access URLs:"
    echo "   Frontend:      http://localhost:3000"
    echo "   Airflow UI:    http://localhost:8081 (admin/admin)"
    echo "   Keycloak:      http://localhost:8080/admin (admin/admin)"
    echo "   API Health:    http://localhost:5000/health"
    echo ""
    echo "🔧 Management commands:"
    echo "   View logs:     docker-compose logs [service]"
    echo "   Stop all:      docker-compose down"
    echo "   Restart:       docker-compose restart [service]"
    echo "   Health check:  ./scripts/health-check-full.sh"
    echo ""
    echo "📁 Important files:"
    echo "   Environment:   .env"
    echo "   Logs:          ./logs/"
    echo "   DAGs:          ./dags/"
    echo ""

    # Show container status
    echo "📊 Container Status:"
    docker-compose ps

    echo ""
    echo "🎯 Next steps:"
    echo "1. Complete system setup: ./scripts/init-test-data.sh"
    echo "2. Run full tests: ./scripts/run-all-steps.sh"
    echo "3. Monitor logs: docker-compose logs -f"
else
    echo ""
    echo "Deployment completed in foreground mode."
fi