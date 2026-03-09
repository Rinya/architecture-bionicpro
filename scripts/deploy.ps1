# BionicPRO Deployment Script - PowerShell version
# This script handles the complete deployment of BionicPRO system on Windows

[CmdletBinding()]
param(
    [switch]$Rebuild,
    [switch]$Pull,
    [switch]$Foreground,
    [switch]$Clean,
    [switch]$Help
)

# Function to display usage
function Show-Usage {
    Write-Host @"
BionicPRO Deployment Script

Usage: .\deploy.ps1 [OPTIONS]

Options:
  -Rebuild       Rebuild all images before starting
  -Pull          Pull latest images before starting
  -Foreground    Run in foreground (not detached)
  -Clean         Clean system (remove volumes and networks) before deploy
  -Help          Display this help message

Examples:
  .\deploy.ps1                 Deploy with default settings
  .\deploy.ps1 -Rebuild        Rebuild and deploy
  .\deploy.ps1 -Clean          Clean deploy (removes all data)
"@
    exit 0
}

if ($Help) {
    Show-Usage
}

# Color functions
function Write-Info {
    param($Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param($Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Find project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = ""

if (Test-Path "$ScriptDir\..\docker-compose.yaml") {
    $ProjectRoot = "$ScriptDir\.."
} elseif (Test-Path "$ScriptDir\docker-compose.yaml") {
    $ProjectRoot = $ScriptDir
} else {
    Write-Error "Cannot find docker-compose.yaml file!"
    Write-Host "Please run from project root or scripts folder."
    exit 1
}

Set-Location $ProjectRoot

Write-Host "========================================"
Write-Host "        BionicPRO Deployment"
Write-Host "========================================"
Write-Host ""

# Pre-flight checks
Write-Info "Performing pre-flight checks..."

# Check if Docker is running
try {
    $dockerInfo = docker info 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
}
catch {
    Write-Error "Docker is not running!"
    Write-Host "Please start Docker Desktop and try again."
    exit 1
}

# Check if docker-compose is available
try {
    $composeVersion = docker-compose version 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "docker-compose not found"
    }
}
catch {
    Write-Error "docker-compose is not installed!"
    Write-Host "Please install docker-compose and try again."
    exit 1
}

# Check .env file
if (-not (Test-Path ".env")) {
    Write-Warning ".env file not found!"
    if (Test-Path ".env.example") {
        Write-Host "Copying .env.example to .env..."
        Copy-Item ".env.example" ".env"
        Write-Warning "Please edit .env file with your configuration before continuing!"
        Read-Host "Press Enter to continue or Ctrl+C to abort"
    } else {
        Write-Error "No .env.example file found!"
        exit 1
    }
}

# Clean deployment if requested
if ($Clean) {
    Write-Warning "Clean deployment requested!"
    Write-Host "This will remove all containers, volumes, and networks."
    $confirmation = Read-Host "Are you sure? (y/N)"
    if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
        Write-Info "Cleaning up existing deployment..."
        docker-compose down -v --remove-orphans 2>$null
        docker volume prune -f 2>$null
        docker network prune -f 2>$null
        Write-Success "Cleanup completed"
    } else {
        Write-Host "Cleanup cancelled."
        exit 0
    }
}

# Pull images if requested
if ($Pull) {
    Write-Info "Pulling latest images..."
    docker-compose pull
    Write-Success "Images pulled"
}

# Stop existing containers
Write-Info "Stopping existing containers..."
docker-compose down 2>$null

# Build or rebuild images
if ($Rebuild) {
    Write-Info "Rebuilding all images..."
    docker-compose build --no-cache
    Write-Success "Images rebuilt"
} else {
    Write-Info "Building images (if needed)..."
    docker-compose build
    Write-Success "Images ready"
}

# Create required directories
Write-Info "Creating required directories..."
$directories = @("logs", "dags", "plugins", "sql")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Success "Directories created"

# Set Airflow UID
Write-Info "Configuring Airflow permissions..."
$envContent = Get-Content ".env" -ErrorAction SilentlyContinue
if ($envContent -and ($envContent | Select-String "^AIRFLOW_UID=")) {
    Write-Success "AIRFLOW_UID already configured"
} else {
    Add-Content ".env" "AIRFLOW_UID=50000"
    Write-Success "AIRFLOW_UID configured"
}

# Start services
Write-Info "Starting BionicPRO services..."

if ($Foreground) {
    Write-Host "Starting in foreground mode (use Ctrl+C to stop)..."
    docker-compose up
} else {
    docker-compose up -d
    Write-Success "Services started in background"

    # Wait for services to be ready
    Write-Info "Waiting for services to be ready..."
    Start-Sleep 10

    # Quick health check
    Write-Info "Performing quick health check..."

    $endpoints = @(
        @{name="Frontend"; url="http://localhost:3000"},
        @{name="Keycloak"; url="http://localhost:8080/realms/reports-realm"},
        @{name="Airflow"; url="http://localhost:8081/health"},
        @{name="API"; url="http://localhost:5000/health"},
        @{name="ClickHouse"; url="http://localhost:8123/ping"}
    )

    $servicesReady = 0
    $totalServices = $endpoints.Count

    foreach ($endpoint in $endpoints) {
        try {
            $response = Invoke-WebRequest -Uri $endpoint.url -TimeoutSec 5 -UseBasicParsing
            Write-Success "$($endpoint.name) is ready"
            $servicesReady++
        }
        catch {
            Write-Error "$($endpoint.name) is not ready"
        }
    }

    Write-Host ""
    Write-Host "Services ready: $servicesReady/$totalServices"
}

# Display final information
Write-Host ""
Write-Host "========================================"
Write-Host "        Deployment Complete!"
Write-Host "========================================"
Write-Host ""

if (-not $Foreground) {
    Write-Success "BionicPRO has been deployed successfully!"
    Write-Host ""
    Write-Host "🌐 Access URLs:"
    Write-Host "   Frontend:      http://localhost:3000"
    Write-Host "   Airflow UI:    http://localhost:8081 (admin/admin)"
    Write-Host "   Keycloak:      http://localhost:8080/admin (admin/admin)"
    Write-Host "   API Health:    http://localhost:5000/health"
    Write-Host ""
    Write-Host "🔧 Management commands:"
    Write-Host "   View logs:     docker-compose logs [service]"
    Write-Host "   Stop all:      docker-compose down"
    Write-Host "   Restart:       docker-compose restart [service]"
    Write-Host "   Health check:  .\scripts\health-check-full.ps1"
    Write-Host ""
    Write-Host "📁 Important files:"
    Write-Host "   Environment:   .env"
    Write-Host "   Logs:          .\logs\"
    Write-Host "   DAGs:          .\dags\"
    Write-Host ""

    # Show container status
    Write-Host "📊 Container Status:"
    docker-compose ps

    Write-Host ""
    Write-Host "🎯 Next steps:"
    Write-Host "1. Complete system setup: .\checks\init-test-data.bat"
    Write-Host "2. Run full tests: .\checks\run-all-steps.bat"
    Write-Host "3. Monitor logs: docker-compose logs -f"
} else {
    Write-Host ""
    Write-Host "Deployment completed in foreground mode."
}