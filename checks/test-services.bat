@echo off
setlocal enabledelayedexpansion

REM Определить правильную рабочую директорию (для совместимости)
set "script_dir=%~dp0"
if exist "%script_dir%..\docker-compose.yaml" (
    cd /d "%script_dir%.."
) else if exist "%script_dir%docker-compose.yaml" (
    cd /d "%script_dir%"
)

echo ========================================
echo          BionicPRO Services Test
echo ========================================
echo.

echo Testing Keycloak...
curl -s http://localhost:8080/realms/reports-realm > nul
if %ERRORLEVEL%==0 (
    echo [✓] Keycloak - OK
) else (
    echo [✗] Keycloak - FAILED
)

echo.
echo Testing Airflow...
curl -s http://localhost:8081/health > nul
if %ERRORLEVEL%==0 (
    echo [✓] Airflow - OK
) else (
    echo [✗] Airflow - FAILED
)

echo.
echo Testing ClickHouse...
curl -s http://localhost:8123/ping > nul
if %ERRORLEVEL%==0 (
    echo [✓] ClickHouse - OK
) else (
    echo [✗] ClickHouse - FAILED
)

echo.
echo Testing Frontend...
curl -s http://localhost:3000 > nul
if %ERRORLEVEL%==0 (
    echo [✓] Frontend - OK
) else (
    echo [✗] Frontend - FAILED
)

echo.
echo Testing Reports API...
curl -s http://localhost:5000/health > nul
if %ERRORLEVEL%==0 (
    echo [✓] Reports API - OK
) else (
    echo [✗] Reports API - FAILED
)

echo.
echo ========================================
echo           Test Complete
echo ========================================
echo.
echo Press any key to exit...
pause > nul