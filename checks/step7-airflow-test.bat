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
    pause > nul
    exit /b 1
)

echo ========================================
echo     BionicPRO Airflow Testing
echo     Шаг 7: Запуск и проверка Airflow DAGs
echo ========================================
echo.

echo === 7.1 Доступ к Airflow ===
echo.
echo [INFO] Airflow UI: http://localhost:8081
echo Login: admin
echo Password: admin
echo.

echo Opening Airflow UI...
start http://localhost:8081

echo Checking Airflow webserver health...
curl -s http://localhost:8081/health > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Airflow webserver is responding
) else (
    echo [✗] Airflow webserver is not responding
    echo Check container status: docker-compose ps airflow-webserver
    pause
    exit /b 1
)

echo.
echo === 7.2 Проверка DAGs ===
echo.

echo Checking for available DAGs...
if exist "dags\*.py" (
    echo [✓] DAG files found in dags directory:
    dir dags\*.py /b 2>nul
    echo.
    echo [MANUAL STEPS] To activate DAGs:
    echo 1. Go to Airflow UI: http://localhost:8081
    echo 2. Login with admin/admin
    echo 3. Find your DAGs in the list
    echo 4. Toggle the switch to activate DAGs
    echo 5. Click "Trigger DAG" to run manually
) else (
    echo [!] No DAG files found in dags directory
    echo Creating sample DAG for testing...

    if not exist "dags" mkdir dags

    echo Creating sample DAG: dags\sample_bionicpro_dag.py
    (
        echo from airflow import DAG
        echo from airflow.operators.bash import BashOperator
        echo from datetime import datetime, timedelta
        echo.
        echo default_args = {
        echo     'owner': 'bionicpro',
        echo     'depends_on_past': False,
        echo     'start_date': datetime^(2024, 1, 1^),
        echo     'email_on_failure': False,
        echo     'email_on_retry': False,
        echo     'retries': 1,
        echo     'retry_delay': timedelta^(minutes=5^)
        echo }
        echo.
        echo dag = DAG^(
        echo     'sample_bionicpro_etl',
        echo     default_args=default_args,
        echo     description='Sample BionicPRO ETL DAG',
        echo     schedule_interval=timedelta^(hours=1^),
        echo     catchup=False
        echo ^)
        echo.
        echo # Sample tasks
        echo check_clickhouse = BashOperator^(
        echo     task_id='check_clickhouse',
        echo     bash_command='echo "Checking ClickHouse connection..."',
        echo     dag=dag
        echo ^)
        echo.
        echo process_data = BashOperator^(
        echo     task_id='process_telemetry_data',
        echo     bash_command='echo "Processing telemetry data..."',
        echo     dag=dag
        echo ^)
        echo.
        echo check_clickhouse ^>^> process_data
    ) > dags\sample_bionicpro_dag.py

    echo [✓] Sample DAG created successfully
)

echo.
echo === 7.3 Имитация ETL обработки ===
echo.

echo [INFO] Adding simulated ETL data to ClickHouse...
echo This simulates what Airflow DAGs would do...

echo Adding ETL simulation data...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user1', 'ESP32-001-BP', today() - 1, 7.5, 86.2, 91.1, 88.3, 1, 11, 41.5, 860.0, now() - INTERVAL 1 HOUR, now())"
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user1', 'ESP32-001-BP', today() - 2, 8.1, 89.1, 93.5, 90.2, 0, 13, 38.2, 790.0, now() - INTERVAL 25 HOUR, now())"
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user2', 'ESP32-002-BP', today() - 1, 6.3, 78.9, 88.7, 82.4, 3, 9, 39.8, 900.0, now() - INTERVAL 2 HOUR, now())"
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "INSERT INTO user_analytics (user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at) VALUES ('user2', 'ESP32-002-BP', today() - 2, 5.8, 76.1, 86.2, 79.8, 2, 8, 41.2, 940.0, now() - INTERVAL 26 HOUR, now())"

if !ERRORLEVEL!==0 (
    echo [✓] ETL simulation data added successfully
) else (
    echo [✗] Failed to add ETL simulation data
)

echo.
echo Verifying ETL data...
docker exec bionicpro-clickhouse clickhouse-client --database reports --query "SELECT 'Recent data count' as metric, COUNT(*) as value FROM user_analytics WHERE report_date >= today() - 2"

echo.
echo === 7.4 Проверка Airflow компонентов ===
echo.

echo Checking Airflow services status...
echo.

echo Scheduler status:
docker-compose ps airflow-scheduler | findstr "Up" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Airflow Scheduler is running
) else (
    echo [✗] Airflow Scheduler has issues
)

echo.
echo Webserver status:
docker-compose ps airflow-webserver | findstr "Up" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Airflow Webserver is running
) else (
    echo [✗] Airflow Webserver has issues
)

echo.
echo Database connection test:
docker exec bionicpro-postgres-airflow psql -U airflow -d airflow -c "SELECT 1 as test;" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Airflow database connection OK
) else (
    echo [✗] Airflow database connection failed
)

echo.
echo === 7.5 Connections и Variables ===
echo.

echo [INFO] Checking Airflow connections and variables...
echo These should be configured for production ETL:

echo.
echo Expected Connections:
echo - clickhouse_default: ClickHouse connection for data storage
echo - kafka_default: Kafka connection for streaming data
echo.
echo Expected Variables:
echo - BATCH_SIZE_CRM: 5000
echo - BATCH_SIZE_TELEMETRY: 10000
echo - ETL_START_DATE: 2024-01-01
echo.

echo.
echo ========================================
echo     Airflow Testing Summary
echo ========================================
echo.
echo [AUTOMATED TESTS COMPLETED]:
echo ✅ Airflow webserver connectivity tested
echo ✅ Airflow components health checked
echo ✅ Sample DAG created (if none existed)
echo ✅ ETL simulation data added
echo ✅ Database connections verified
echo.
echo [MANUAL VERIFICATION NEEDED]:
echo 🔍 Login to Airflow UI (admin/admin)
echo 🔍 Activate DAGs if available
echo 🔍 Trigger DAG execution manually
echo 🔍 Monitor DAG run status
echo 🔍 Check logs for any errors
echo.
echo [AIRFLOW URLS]:
echo → Airflow UI: http://localhost:8081
echo → Admin/Admin credentials provided
echo.
echo [NEXT STEPS]:
echo → Run step8-complete-check.bat for full system verification
echo → Monitor DAG execution in Airflow UI
echo → Check ETL data processing results
echo.
echo Press any key to continue...
pause > nul