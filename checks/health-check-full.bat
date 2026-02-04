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
echo     BionicPRO Full Health Check
echo ========================================
echo.

echo ========================================
echo    3.1 Endpoint Health Checks
echo ========================================
echo.

echo Testing Frontend...
curl -s http://localhost:3000 > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Frontend - OK ^(http://localhost:3000^)
) else (
    echo [✗] Frontend - FAILED ^(http://localhost:3000^)
)

echo.
echo Testing Keycloak...
curl -s http://localhost:8080/realms/reports-realm > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Keycloak - OK ^(http://localhost:8080/realms/reports-realm^)
) else (
    echo [✗] Keycloak - FAILED ^(http://localhost:8080/realms/reports-realm^)
)

echo.
echo Testing Airflow...
curl -s http://localhost:8081/health > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Airflow - OK ^(http://localhost:8081/health^)
) else (
    echo [✗] Airflow - FAILED ^(http://localhost:8081/health^)
)

echo.
echo Testing Reports API...
curl -s http://localhost:5000/health > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Reports API - OK ^(http://localhost:5000/health^)
) else (
    echo [✗] Reports API - FAILED ^(http://localhost:5000/health^)
)

echo.
echo Testing ClickHouse...
curl -s http://localhost:8123/ping > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] ClickHouse - OK ^(http://localhost:8123/ping^)
) else (
    echo [✗] ClickHouse - FAILED ^(http://localhost:8123/ping^)
)

echo.
echo ========================================
echo    3.2 Docker Container Status
echo ========================================
echo.
echo Container status check...
docker-compose ps
echo.

echo Recent logs check (last 10 lines per service)...
echo.
echo --- Keycloak Logs ---
docker-compose logs --tail=10 keycloak 2>nul
echo.
echo --- ClickHouse Logs ---
docker-compose logs --tail=10 clickhouse 2>nul
echo.
echo --- Reports API Logs ---
docker-compose logs --tail=10 reports-api 2>nul
echo.
echo --- Airflow Scheduler Logs ---
docker-compose logs --tail=10 airflow-scheduler 2>nul
echo.

echo ========================================
echo    3.3 Database Health Checks
echo ========================================
echo.

echo Testing ClickHouse database...
docker-compose exec -T clickhouse clickhouse-client --query "SHOW DATABASES" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] ClickHouse Database - OK
    echo Available databases:
    docker-compose exec -T clickhouse clickhouse-client --query "SHOW DATABASES"
) else (
    echo [✗] ClickHouse Database - FAILED
)

echo.
echo Testing PostgreSQL ^(Airflow^)...
docker-compose exec -T postgres-airflow psql -U airflow -d airflow -c "\dt" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] PostgreSQL Airflow - OK
    echo Available tables ^(sample^):
    docker-compose exec -T postgres-airflow psql -U airflow -d airflow -c "\dt"
) else (
    echo [✗] PostgreSQL Airflow - FAILED
)

echo.
echo Testing PostgreSQL ^(Keycloak^)...
docker-compose exec -T keycloak_db psql -U keycloak_user -d keycloak_db -c "\dt" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] PostgreSQL Keycloak - OK
    echo Available tables ^(sample^):
    docker-compose exec -T keycloak_db psql -U keycloak_user -d keycloak_db -c "\dt"
) else (
    echo [✗] PostgreSQL Keycloak - FAILED
)

echo.
echo Testing Redis...
docker-compose exec -T redis redis-cli -a bionicpro_redis_password ping > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Redis - OK ^(default password^)
    echo Redis info:
    docker-compose exec -T redis redis-cli -a bionicpro_redis_password info server | findstr "redis_version"
) else (
    echo [!] Redis - FAILED with default password
    echo Note: If you changed REDIS_PASSWORD in .env, Redis may still be working
    echo Try: docker exec -it bionicpro-redis redis-cli -a your_redis_password ping
)

echo.
echo ========================================
echo    Additional System Information
echo ========================================
echo.

echo Docker system info:
docker system df

echo.
echo Network information:
docker network ls | findstr bionicpro

echo.
echo Volume information:
docker volume ls | findstr bionicpro

echo.
echo ========================================
echo        Health Check Complete
echo ========================================
echo.

echo Summary of critical endpoints:
echo - Frontend:     http://localhost:3000
echo - Backend API:  http://localhost:5000/health
echo - Airflow UI:   http://localhost:8081
echo - Keycloak:     http://localhost:8080/admin
echo - ClickHouse:   http://localhost:8123/play
echo.

echo Press any key to exit...
pause > nul