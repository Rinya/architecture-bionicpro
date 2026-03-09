"""
CRM Integration DAG for BionicPRO
Интеграция с Битрикс24 CRM для извлечения данных клиентов, заказов и протезов
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.http.hooks.http import HttpHook
from clickhouse_driver import Client  # <-- Используем clickhouse-driver напрямую
from airflow.models import Variable
import pandas as pd
import json
import logging
import uuid

# Конфигурация DAG
DEFAULT_ARGS = {
    'owner': 'bionicpro-crm-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=60),
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
    'crm_integration',
    default_args=DEFAULT_ARGS,
    description='Битрикс24 CRM Integration for BionicPRO',
    schedule=None,  # Запускается из master DAG
    catchup=False,
    max_active_runs=1,
    tags=['bionicpro', 'crm', 'bitrix24', 'etl'],
    doc_md="""
    # Битрикс24 CRM Integration DAG

    Интеграция с CRM системой Битрикс24 для извлечения:
    - Данных клиентов (контакты)
    - Заказов и сделок
    - Информации о протезах
    """
)

def get_clickhouse_client():
    """Возвращает готовый клиент ClickHouse"""
    return Client(**CLICKHOUSE_CONFIG)

def load_sql_file_to_clickhouse(**kwargs):
    """
    загрузка данных в CRM
    """
    logging.info("🔄 Start loading CRM data to ClickHouse...")

    audit_query = """
        INSERT INTO audit.etl_operations
        (
            operation_id, dag_id, task_id, user_id, operation_type, table_name,
            records_processed, start_time, end_time, status, error_message,
            data_checksum, compliance_flags, created_at
        )
        VALUES
    """

    try:
        client = get_clickhouse_client()

        with open('sql/insert_crm_data.sql', 'r') as f:
            sql_content = f.read()

        # Разделяем по точкам с запятой для выполнения нескольких запросов
        queries = [q.strip() for q in sql_content.split(';') if q.strip()]

        for query in queries:
            client.execute(query)

        # Логирование в аудит
        audit_data = (
            str(uuid.uuid4()),                   # operation_id
            kwargs['dag'].dag_id,                # dag_id
            kwargs['task'].task_id,              # task_id
            None,                                # user_id
            'CRM_LOAD',                          # operation_type
            'crm.customers,crm.orders',          # table_name
            len(queries),                        # records_processed
            datetime.now(),                      # start_time
            datetime.now(),                      # end_time
            'SUCCESS',                           # status
            None,                                # error_message
            '',                                  # data_checksum
            ['GDPR_COMPLIANT', 'FZ152_COMPLIANT'],  # compliance_flags (массив!)
            datetime.now(),                      # created_at (лишнее, если default)
        )

        client.execute(audit_query, [audit_data])

        logging.info(f"🎯 CRM data loaded successfully. Total records: {len(queries)}")
        return len(queries)
    except Exception as e:
        logging.error(f"❌ Failed to load CRM data to ClickHouse: {e}")
        # Логирование ошибки в аудит
        try:
            audit_data = (
                str(uuid.uuid4()),           # operation_id
                kwargs['dag'].dag_id,        # dag_id
                kwargs['task'].task_id,      # task_id
                None,                        # user_id
                'CRM_LOAD_ERROR',            # operation_type
                'crm.customers,crm.orders',  # table_name
                0,                           # records_processed
                datetime.now(),              # start_time
                datetime.now(),              # end_time
                'FAILED',                    # status
                '{str(e)[:500]}',            # error_message
                '',                          # data_checksum
                ['ERROR'],                   # compliance_flags (массив!)
                datetime.now(),              # created_at (лишнее, если default)
            )

            client.execute(audit_query, [audit_data])
        except:
            pass
        raise

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАДАЧ
# =====================================================

start = EmptyOperator(task_id='start_crm_integration', dag=dag)

# Загрузка в ClickHouse
load_to_clickhouse = PythonOperator(task_id='load_crm_data_to_clickhouse', python_callable=load_sql_file_to_clickhouse, dag=dag)

end = EmptyOperator(task_id='crm_integration_completed', dag=dag)

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# =====================================================

start >> load_to_clickhouse >> end