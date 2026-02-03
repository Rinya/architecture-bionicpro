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
echo    BionicPRO Troubleshoot Checker
echo ========================================
echo.

echo ========================================
echo    Port Availability Check
echo ========================================
echo.

set "ports=3000 5000 5433 5434 6380 8080 8081 8123 9000 9092"

echo Checking if required ports are free...
for %%p in (%ports%) do (
    netstat -an | findstr :%%p > nul
    if !ERRORLEVEL!==0 (
        echo [!] Port %%p is occupied
        netstat -ano | findstr :%%p | findstr LISTENING
    ) else (
        echo [✓] Port %%p is free
    )
)

echo.
echo ========================================
echo    Memory and Disk Space Check
echo ========================================
echo.

echo Available memory:
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /format:list | findstr "="

echo.
echo Disk space for Docker:
docker system df

echo.
echo ========================================
echo    Docker Network Check
echo ========================================
echo.

echo Checking Docker networks...
docker network ls | findstr bionicpro > nul
if !ERRORLEVEL!==0 (
    echo [✓] BionicPRO networks exist
    docker network ls | findstr bionicpro
) else (
    echo [!] BionicPRO networks not found
    echo Available networks:
    docker network ls
)

echo.
echo ========================================
echo    Environment Variables Check
echo ========================================
echo.

if exist .env (
    echo [✓] .env file exists
    echo Checking critical variables...

    findstr "JWT_SECRET_KEY" .env > nul
    if !ERRORLEVEL!==0 (
        echo [✓] JWT_SECRET_KEY is set
    ) else (
        echo [!] JWT_SECRET_KEY is missing
    )

    findstr "POSTGRES_KEYCLOAK_PASSWORD" .env > nul
    if !ERRORLEVEL!==0 (
        echo [✓] POSTGRES_KEYCLOAK_PASSWORD is set
    ) else (
        echo [!] POSTGRES_KEYCLOAK_PASSWORD is missing
    )

    findstr "POSTGRES_AIRFLOW_PASSWORD" .env > nul
    if !ERRORLEVEL!==0 (
        echo [✓] POSTGRES_AIRFLOW_PASSWORD is set
    ) else (
        echo [!] POSTGRES_AIRFLOW_PASSWORD is missing
    )

    findstr "CLICKHOUSE_PASSWORD" .env > nul
    if !ERRORLEVEL!==0 (
        echo [✓] CLICKHOUSE_PASSWORD is set
    ) else (
        echo [!] CLICKHOUSE_PASSWORD is missing
    )

    findstr "REDIS_PASSWORD" .env > nul
    if !ERRORLEVEL!==0 (
        echo [✓] REDIS_PASSWORD is set
    ) else (
        echo [!] REDIS_PASSWORD is missing
    )

    findstr "AIRFLOW_UID" .env > nul
    if !ERRORLEVEL!==0 (
        echo [✓] AIRFLOW_UID is set
    ) else (
        echo [!] AIRFLOW_UID is missing - this will cause startup issues
    )

) else (
    echo [✗] .env file not found!
    echo Please copy .env.example to .env and configure it.
)

echo.
echo ========================================
echo    Container Health Details
echo ========================================
echo.

echo Unhealthy containers:
docker-compose ps | findstr "unhealthy\|Exit"

echo.
echo Recent container events ^(last 10 minutes^):
docker events --since 10m --until 0s 2>nul

echo.
echo ========================================
echo    Volume and Permission Check
echo ========================================
echo.

echo Docker volumes:
docker volume ls | findstr bionicpro

echo.
if exist logs (
    echo [✓] logs directory exists
) else (
    echo [!] logs directory missing
    mkdir logs
    echo [✓] logs directory created
)

if exist dags (
    echo [✓] dags directory exists
) else (
    echo [!] dags directory missing
    mkdir dags
    echo [✓] dags directory created
)

if exist plugins (
    echo [✓] plugins directory exists
) else (
    echo [!] plugins directory missing
    mkdir plugins
    echo [✓] plugins directory created
)

echo.
echo ========================================
echo    Quick Fix Suggestions
echo ========================================
echo.

echo Common fixes:
echo 1. If ports are occupied: Stop conflicting services
echo 2. If memory issues: docker system prune -a
echo 3. If network issues: docker network create bionicpro-network
echo 4. If AIRFLOW_UID missing: echo AIRFLOW_UID=50000 ^>^> .env
echo 5. If containers unhealthy: docker-compose restart ^<service^>
echo.

echo For detailed logs of a specific service:
echo   docker-compose logs ^<service-name^>
echo.
echo For complete restart:
echo   docker-compose down ^&^& docker-compose up -d
echo.

echo Press any key to exit...
pause > nul