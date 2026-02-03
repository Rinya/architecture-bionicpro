@echo off
setlocal enabledelayedexpansion

REM Определить правильную рабочую директорию
set "script_dir=%~dp0"
if exist "%script_dir%..\docker-compose.yaml" (
    cd /d "%script_dir%.."
) else if exist "%script_dir%docker-compose.yaml" (
    cd /d "%script_dir%"
) else (
    echo [ERROR] Cannot find docker-compose.yaml file!
    echo Please run from project root or checks folder.
    pause > nul
    exit /b 1
)
echo ========================================
echo     BionicPRO Quick Health Check
echo ========================================
echo.

echo Testing all endpoints...
echo.

set "endpoints[0]=Frontend;http://localhost:3000"
set "endpoints[1]=Keycloak;http://localhost:8080/realms/reports-realm"
set "endpoints[2]=Airflow;http://localhost:8081/health"
set "endpoints[3]=Reports API;http://localhost:5000/health"
set "endpoints[4]=ClickHouse;http://localhost:8123/ping"

set "success_count=0"
set "total_count=5"

for /L %%i in (0,1,4) do (
    for /f "tokens=1,2 delims=;" %%a in ("!endpoints[%%i]!") do (
        echo Testing %%a...
        curl -s --max-time 5 %%b > nul 2>&1
        if !ERRORLEVEL!==0 (
            echo [✓] %%a - OK
            set /a success_count+=1
        ) else (
            echo [✗] %%a - FAILED ^(%%b^)
        )
        echo.
    )
)

echo ========================================
echo Container Status Summary:
echo ========================================
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ========================================
echo           Summary
echo ========================================
set /a failed_count=!total_count!-!success_count!
echo Services tested: !total_count!
echo Services OK: !success_count!
echo Services FAILED: !failed_count!

if !success_count!==!total_count! (
    echo.
    echo [✓] ALL SYSTEMS OPERATIONAL
    echo System is ready to use!
) else (
    echo.
    echo [!] SOME SERVICES FAILED
    echo Check the detailed output above.
    echo Run 'checks\health-check-full.bat' for detailed diagnostics.
)

echo.
echo Quick access URLs:
echo - Frontend:    http://localhost:3000
echo - Airflow UI:  http://localhost:8081
echo - Keycloak:    http://localhost:8080/admin
echo.
echo Press any key to exit...
pause > nul