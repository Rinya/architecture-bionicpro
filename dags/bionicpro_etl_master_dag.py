"""
BionicPRO ETL Master DAG
Основной оркестратор ETL процессов для системы отчетности BionicPRO
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.http.hooks.http import HttpHook
from clickhouse_driver import Client  # <-- Используем clickhouse-driver напрямую
import logging
import uuid

# Конфигурация DAG
DEFAULT_ARGS = {
    'owner': 'bionicpro-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
}

# Настройки подключения к ClickHouse (можно вынести в Airflow Connections, но для простоты — здесь)
CLICKHOUSE_CONFIG = {
    'host': 'clickhouse',
    'port': 9000,
    'user': 'reports_user',
    'password': 'secure_reports_password_2024!',  # ⚠️ Лучше использовать Airflow Connection + get_password()
    'database': 'reports',
    'settings': {'max_execution_time': 300},
    'connect_timeout': 10,
    'send_receive_timeout': 300,
    'sync_request_timeout': 300,
    'compression': True,  # Включить сжатие для производительности
}

# Создание DAG
dag = DAG(
    'bionicpro_etl_master',
    default_args=DEFAULT_ARGS,
    description='BionicPRO ETL Master Orchestrator',
    schedule='*/15 * * * *',  # Каждые 15 минут
    catchup=False,
    max_active_runs=1,
    tags=['bionicpro', 'etl', 'master'],
    doc_md="""
    # BionicPRO ETL Master DAG

    Основной оркестратор ETL процессов для системы отчетности BionicPRO.

    ## Выполняемые задачи:
    1. Проверка состояния системы
    2. Запуск ETL процессов в правильной последовательности
    3. Мониторинг выполнения
    4. Уведомления о статусе

    ## Частота выполнения:
    Каждые 15 минут (соответствует требованиям бизнеса)

    ## Зависимости:
    - ClickHouse (витрина данных)
    - Kafka (потоковые данные)
    - Битрикс24 (CRM данные)
    - PostgreSQL (пользователи)
    """
)

def get_clickhouse_client():
    """Возвращает готовый клиент ClickHouse"""
    return Client(**CLICKHOUSE_CONFIG)

def check_system_health(**kwargs):
    """
    Проверка состояния всех компонентов системы перед запуском ETL
    """
    logging.info("🔍 Checking system health before ETL execution...")

    health_status = {}
    errors = []

    try:
        # Проверка ClickHouse
        client = get_clickhouse_client()
        client.execute("SELECT 1")
        health_status['clickhouse'] = 'OK'
        logging.info("✅ ClickHouse connection: OK")
    except Exception as e:
        health_status['clickhouse'] = 'ERROR'
        errors.append(f"ClickHouse: {str(e)}")
        logging.error(f"❌ ClickHouse connection failed: {e}")

    try:
        # Проверка PostgreSQL (Keycloak DB для пользователей)
        postgres_hook = PostgresHook(postgres_conn_id='keycloak_db')
        postgres_hook.run("SELECT 1")
        health_status['postgresql'] = 'OK'
        logging.info("✅ PostgreSQL connection: OK")
    except Exception as e:
        health_status['postgresql'] = 'ERROR'
        errors.append(f"PostgreSQL: {str(e)}")
        logging.error(f"❌ PostgreSQL connection failed: {e}")

    # Сохранение статуса в XCom для использования в других задачах
    kwargs['ti'].xcom_push(key='health_status', value=health_status)
    kwargs['ti'].xcom_push(key='health_errors', value=errors)

    # Если критические системы недоступны, прерываем выполнение
    if health_status['clickhouse'] == 'ERROR' or health_status['postgresql'] == 'ERROR':
        raise Exception(f"Critical system health check failed: {errors}")

    logging.info(f"🎯 System health check completed. Status: {health_status}")
    return health_status

def calculate_etl_priority(**kwargs):
    """
    Определение приоритета и порядка выполнения ETL процессов
    """
    logging.info("📊 Calculating ETL execution priority...")

    # Получение статуса системы из предыдущей задачи
    health_status = kwargs['ti'].xcom_pull(
        task_ids='check_system_health',
        key='health_status'
    )

    # Определение приоритета задач
    etl_priority = []

    # Высокий приоритет: обработка телеметрии (реал-тайм данные)
    etl_priority.append({
        'dag_id': 'telemetry_processing',
        'priority': 10,
        'enabled': True,
        'reason': 'Real-time telemetry processing'
    })

    # Низкий приоритет: создание отчетов (зависит от данных)
    etl_priority.append({
        'dag_id': 'reports_mart',
        'priority': 8,
        'enabled': True,
        'reason': 'Reports generation'
    })

    # Очень низкий приоритет: аудит и compliance
    etl_priority.append({
        'dag_id': 'compliance_audit',
        'priority': 3,
        'enabled': True,
        'reason': 'Audit and compliance'
    })

    # Сортировка по приоритету
    etl_priority.sort(key=lambda x: x['priority'], reverse=True)

    kwargs['ti'].xcom_push(key='etl_priority', value=etl_priority)

    logging.info(f"🎯 ETL priority calculated: {etl_priority}")
    return etl_priority

def log_etl_start(ds, **kwargs):
    """
    Логирование начала ETL процесса
    """
    execution_date = datetime.strptime(ds, "%Y-%m-%d")
    dag_run_id = kwargs['dag_run'].run_id

    logging.info(f"🚀 Starting BionicPRO ETL Master execution")
    logging.info(f"📅 Execution date: {execution_date}")
    logging.info(f"🔖 DAG run ID: {dag_run_id}")

    audit_query = """
        INSERT INTO audit.etl_operations
        (
            operation_id, dag_id, task_id, user_id, operation_type, table_name,
            records_processed, start_time, end_time, status, error_message,
            data_checksum, compliance_flags, created_at
        )
        VALUES
    """

    # Запись в ClickHouse для аудита
    try:
        client = get_clickhouse_client()

        # Логирование в аудит
        audit_data = (
            dag_run_id,                                     # operation_id
            'bionicpro_etl_master',                         # dag_id
            'etl_start',                                    # task_id
            None,                                           # user_id
            'MASTER_START',                                 # operation_type
            'N/A',                                          # table_name
            0,                                              # records_processed
            execution_date,                                 # start_time
            None,                                           # end_time
            'STARTED',                                      # status
            None,                                           # error_message
            '',                                             # data_checksum
            ['GDPR_COMPLIANT', 'FZ152_COMPLIANT'],          # compliance_flags (массив!)
            datetime.now(),                                 # created_at (лишнее, если default)
        )

        client.execute(audit_query, [audit_data])
        logging.info("✅ ETL start logged to audit table")
    except Exception as e:
        logging.warning(f"⚠️ Failed to log ETL start: {e}")

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАДАЧ DAG
# =====================================================

start = EmptyOperator(task_id='start', dag=dag)

# Проверка состояния системы
health_check = PythonOperator(
    task_id='check_system_health',
    python_callable=check_system_health,
    dag=dag,
    doc_md="Проверка доступности всех компонентов системы"
)

# Логирование старта ETL
log_start = PythonOperator(
    task_id='log_etl_start',
    python_callable=log_etl_start,
    op_kwargs={'ds': '{{ ds }}'},  # или '{{ execution_date }}'
    dag=dag,
    doc_md="Логирование начала ETL процесса в audit таблицу"
)

# Расчет приоритета выполнения
priority_calc = PythonOperator(
    task_id='calculate_etl_priority',
    python_callable=calculate_etl_priority,
    dag=dag,
    doc_md="Определение порядка и приоритета выполнения ETL процессов"
)

# Запуск обработки телеметрии (высокий приоритет)
trigger_telemetry = TriggerDagRunOperator(
    task_id='trigger_telemetry_processing',
    trigger_dag_id='telemetry_processing',
    wait_for_completion=False,  # Не ждем завершения для параллельности
    dag=dag,
    doc_md="Запуск обработки телеметрии от ESP32 протезов"
)

# Запуск интеграции с CRM
trigger_crm = TriggerDagRunOperator(
    task_id='trigger_crm_integration',
    trigger_dag_id='crm_integration',
    wait_for_completion=False,
    dag=dag,
    doc_md="Запуск интеграции с Битрикс24 CRM"
)

# Запуск создания отчетов (выполняется после основных ETL)
trigger_reports = TriggerDagRunOperator(
    task_id='trigger_reports_mart',
    trigger_dag_id='reports_mart',
    wait_for_completion=True,  # Ждем завершения для проверки результата
    dag=dag,
    doc_md="Запуск создания витрины отчетов"
)

# Запуск аудита и compliance
trigger_audit = TriggerDagRunOperator(
    task_id='trigger_compliance_audit',
    trigger_dag_id='compliance_audit',
    wait_for_completion=False,
    dag=dag,
    doc_md="Запуск процессов аудита и GDPR/152-ФЗ compliance"
)

completion = EmptyOperator(
    task_id='etl_completed',
    dag=dag,
    trigger_rule='all_done',  # Выполняется даже если некоторые задачи failed
    doc_md="Завершение ETL процесса (успешное или с ошибками)"
)

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# =====================================================

# Последовательный старт
start >> health_check >> log_start >> priority_calc

# Параллельный запуск основных ETL процессов
priority_calc >> [trigger_telemetry, trigger_crm]

# Создание отчетов после основных ETL
[trigger_telemetry, trigger_crm] >> trigger_reports

# Аудит выполняется параллельно
priority_calc >> trigger_audit

# Завершение
[trigger_reports, trigger_audit] >> completion

# =====================================================
# НАСТРОЙКИ МОНИТОРИНГА И АЛЕРТОВ
# =====================================================

# SLA для всего DAG
dag.sla_miss_callback = None  # Можно добавить функцию для отправки алертов

# Callback функции для уведомлений
def on_success_callback(kwargs):
    """Callback при успешном завершении DAG"""
    logging.info("🎉 BionicPRO ETL Master completed successfully!")

def on_failure_callback(kwargs):
    """Callback при ошибке в DAG"""
    logging.error("❌ BionicPRO ETL Master failed!")
    # Здесь можно добавить отправку уведомлений в Slack/email

# Установка callbacks
dag.on_success_callback = on_success_callback
dag.on_failure_callback = on_failure_callback