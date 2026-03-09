@echo off
chcp 65001 > nul
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
echo     BionicPRO Test Data Initialization
echo     Шаг 4: Инициализация данных и тестирование
echo ========================================
echo.

echo [INFO] Creating test data in ClickHouse...
echo This may take a few moments...
echo.

REM Создание тестовых данных в ClickHouse
echo === 4.1 Создание тестовых данных в ClickHouse ===
echo.

REM Проверка соединения с ClickHouse
echo Testing ClickHouse connection...
docker exec bionicpro-clickhouse clickhouse-client --query "SELECT 1" > nul
if !ERRORLEVEL! NEQ 0 (
    echo [✗] Failed to connect to ClickHouse. Make sure the container is running.
    pause
    exit /b 1
)
echo [✓] ClickHouse connection successful!

echo Checking existing table...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "SELECT COUNT(*) FROM user_analytics" > nul
if !ERRORLEVEL! == 0 (
    echo [INFO] Table reports.user_analytics already exists. Clearing existing test data...
    docker exec bionicpro-clickhouse clickhouse-client --database reports --query "TRUNCATE TABLE user_analytics"
    if !ERRORLEVEL! NEQ 0 (
        echo [!] Warning: Could not clear existing data
    )
) else (
    echo [INFO] Table does not exist or is empty, continuing...
)

echo Inserting test data...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user1', 'ESP32-001-BP', '2024-01-15', 8.5, 87.2, 92.1, 89.3, 2, 12, 42.5, 850.0, '2024-01-15 23:45:00', now())"
echo Adding user1 day 2...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user1', 'ESP32-001-BP', '2024-01-16', 7.2, 85.1, 90.8, 87.1, 1, 10, 43.2, 820.0, '2024-01-16 23:30:00', now())"
echo Adding user1 day 3...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user1', 'ESP32-001-BP', '2024-01-17', 6.8, 88.5, 93.2, 91.5, 0, 9, 45.3, 780.0, '2024-01-17 22:15:00', now())"
echo Adding user2 day 1...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user2', 'ESP32-002-BP', '2024-01-15', 5.5, 75.2, 85.1, 78.3, 4, 8, 41.0, 920.0, '2024-01-15 23:20:00', now())"
echo Adding user2 day 2...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user2', 'ESP32-002-BP', '2024-01-16', 6.2, 77.8, 87.5, 80.1, 2, 10, 37.2, 880.0, '2024-01-16 22:45:00', now())"

if !ERRORLEVEL!==0 (
    echo [✓] Test data created successfully!
) else (
    echo [✗] Failed to create test data in ClickHouse
    echo Check that ClickHouse container is running and healthy
    pause
    exit /b 1
)

echo.
echo === 4.2 Проверка доступности тестовых данных ===
echo.

echo Verifying test data was created correctly...
echo.

docker exec bionicpro-clickhouse clickhouse-client --database reports --query "SELECT user_id, device_id, count() as report_count, min(report_date) as first_date, max(report_date) as last_date FROM user_analytics GROUP BY user_id, device_id ORDER BY user_id, device_id"

if !ERRORLEVEL!==0 (
    echo [✓] Test data verification completed successfully!
) else (
    echo [✗] Failed to verify test data
    pause
    exit /b 1
)

echo.
echo === Дополнительные тестовые данные (для имитации ETL) ===
echo.

echo Adding recent test data records...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user1', 'ESP32-001-BP', today() - 1, 7.5, 86.2, 91.1, 88.3, 1, 11, 41.5, 860.0, now() - INTERVAL 1 HOUR, now())"
echo Adding yesterday data for user1...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user1', 'ESP32-001-BP', today() - 2, 8.1, 89.1, 93.5, 90.2, 0, 13, 38.2, 790.0, now() - INTERVAL 25 HOUR, now())"

if !ERRORLEVEL!==0 (
    echo [✓] Recent test data added successfully!
) else (
    echo [!] Warning: Could not add recent test data (non-critical)
)

echo.
echo === Summary Report ===
echo.

echo Getting database statistics...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "SELECT COUNT(*) as total_records, COUNT(DISTINCT user_id) as unique_users, COUNT(DISTINCT device_id) as unique_devices, MIN(report_date) as earliest_date, MAX(report_date) as latest_date FROM user_analytics"

echo.
echo ========================================
echo     Test Data Initialization Complete
echo ========================================
echo.
echo [INFO] What was created:
echo - ✅ Table: reports.user_analytics
echo - ✅ Test data for user1 and user2
echo - ✅ Historical data (January 2024)
echo - ✅ Recent data (yesterday, day before yesterday)
echo.
echo [NEXT STEPS]:
echo 1. Test authentication: Proceed to Step 5 (STARTUP_GUIDE.md)
echo 2. Create Keycloak users if needed
echo 3. Test API endpoints with JWT tokens
echo 4. Verify UI functionality at http://localhost:3000
echo.
echo [QUICK TESTS]:
echo - Health check: checks\quick-health-check.bat
echo - API test: checks\health-check-full.bat
echo.
echo Press any key to exit...
pause > nul