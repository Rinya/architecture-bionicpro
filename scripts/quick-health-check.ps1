# BionicPRO Quick Health Check - PowerShell version
# This script performs a quick health check of all BionicPRO services

[CmdletBinding()]
param(
    [switch]$Verbose
)

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
    Write-Host "[✗] $Message" -ForegroundColor Red
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
Write-Host "     BionicPRO Quick Health Check"
Write-Host "========================================"
Write-Host ""

Write-Host "Testing all endpoints..."
Write-Host ""

# Define endpoints to test
$endpoints = @(
    @{name="Frontend"; url="http://localhost:3000"},
    @{name="Keycloak"; url="http://localhost:8080/realms/reports-realm"},
    @{name="Airflow"; url="http://localhost:8081/health"},
    @{name="Reports API"; url="http://localhost:5000/health"},
    @{name="ClickHouse"; url="http://localhost:8123/ping"}
)

$successCount = 0
$totalCount = $endpoints.Count

# Test each endpoint
foreach ($endpoint in $endpoints) {
    Write-Host "Testing $($endpoint.name)..." -NoNewline

    try {
        $response = Invoke-WebRequest -Uri $endpoint.url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host " " -NoNewline
        Write-Success "OK"
        $successCount++
    }
    catch {
        Write-Host " " -NoNewline
        Write-Error "FAILED ($($endpoint.url))"
        if ($Verbose) {
            Write-Host "Error: $($_.Exception.Message)" -ForegroundColor DarkRed
        }
    }
    Write-Host ""
}

Write-Host "========================================"
Write-Host "Container Status Summary:"
Write-Host "========================================"

try {
    $containerStatus = docker-compose ps --format "table {{.Name}}`t{{.Status}}`t{{.Ports}}" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host $containerStatus
    } else {
        Write-Warning "Could not retrieve container status"
    }
}
catch {
    Write-Warning "Docker Compose not available or not in project directory"
}

Write-Host ""
Write-Host "========================================"
Write-Host "           Summary"
Write-Host "========================================"

$failedCount = $totalCount - $successCount
Write-Host "Services tested: $totalCount"
Write-Host "Services OK: $successCount"
Write-Host "Services FAILED: $failedCount"

if ($successCount -eq $totalCount) {
    Write-Host ""
    Write-Success "ALL SYSTEMS OPERATIONAL"
    Write-Host "System is ready to use!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Warning "SOME SERVICES FAILED"
    Write-Host "Check the detailed output above."
    Write-Host "Run '.\checks\health-check-full.bat' for detailed diagnostics."
}

Write-Host ""
Write-Host "Quick access URLs:"
Write-Host "- Frontend:    http://localhost:3000"
Write-Host "- Airflow UI:  http://localhost:8081"
Write-Host "- Keycloak:    http://localhost:8080/admin"
Write-Host ""

# Additional PowerShell-specific information
Write-Host "PowerShell-specific commands:"
Write-Host "- View container logs: docker-compose logs <service>"
Write-Host "- Container status:    docker-compose ps"
Write-Host "- Restart service:     docker-compose restart <service>"
Write-Host "- Stop all:           docker-compose down"
Write-Host ""

# Return appropriate exit code
if ($successCount -eq $totalCount) {
    exit 0
} else {
    exit 1
}