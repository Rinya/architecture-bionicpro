"""
Telemetry Processing DAG for BionicPRO
Обработка потоковых данных телеметрии от ESP32 протезов через Kafka
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from clickhouse_driver import Client  # <-- Используем clickhouse-driver напрямую
from kafka import KafkaConsumer
from typing import List, Dict, Any
import json
import logging
import pandas as pd
import uuid
import random
import csv

# Конфигурация DAG
DEFAULT_ARGS = {
    'owner': 'bionicpro-telemetry-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 5,
    'retry_delay': timedelta(seconds=30),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=10),
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
    'telemetry_processing',
    default_args=DEFAULT_ARGS,
    description='ESP32 Telemetry Processing for BionicPRO',
    schedule=None,  # Запускается из master DAG
    catchup=False,
    max_active_runs=2,  # Допускаем параллельное выполнение
    tags=['bionicpro', 'telemetry', 'esp32', 'real-time'],
    doc_md="""
    # ESP32 Telemetry Processing DAG

    Обработка потоковых данных телеметрии от бионических протезов:
    - Загрузка в ClickHouse
    """
)

def get_clickhouse_client():
    """Возвращает готовый клиент ClickHouse"""
    return Client(**CLICKHOUSE_CONFIG)

def load_telemetry_to_clickhouse(ds, **kwargs):
    """
    Загрузка телеметрии в ClickHouse
    """
    logging.info("💾 Loading telemetry data to ClickHouse...")
    execution_date = datetime.strptime(ds, "%Y-%m-%d")

    audit_query = """
        INSERT INTO audit.etl_operations
        (
            operation_id, dag_id, task_id, user_id, operation_type, table_name,
            records_processed, start_time, end_time, status, error_message,
            data_checksum, compliance_flags, created_at
        )
        VALUES
    """

    total_loaded = 0
    client = get_clickhouse_client()

    try:
        # Загрузка сырых данных телеметрии
        CSV_RAW_FILE_PATH = 'data/telemetry_raw_data.csv'
        with open(CSV_RAW_FILE_PATH, 'r') as csvfile:
            csvreader = csv.reader(csvfile)

            raw_query = """
                INSERT INTO telemetry.raw_data
                (
                    device_id, user_id, timestamp, sensor_type, sensor_value, battery_level, signal_strength,
                    firmware_version, location_lat, location_lon, metadata, received_at
                )
                VALUES
            """

            # Генерим запросы
            is_header = True
            count = 0
            batch = []
            for row in csvreader:
                if is_header:
                    is_header = False
                    continue

                # Преобразуем строки в datetime объекты
                timestamp = datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S') if row[2] else datetime.now()
                received_at = datetime.strptime(row[11], '%Y-%m-%d %H:%M:%S') if row[11] else datetime.now()

                # Обработка пустых значений для координат
                location_lat = None if row[8] == '' else float(row[8]) if row[8] else None
                location_lon = None if row[9] == '' else float(row[9]) if row[9] else None

                raw_data = [
                    row[0],          # device_id
                    row[1],          # user_id
                    timestamp,       # timestamp (как строка)
                    row[3],          # sensor_type
                    float(row[4]),   # sensor_value
                    float(row[5]),   # battery_level
                    int(row[6]),     # signal_strength
                    row[7],          # firmware_version
                    location_lat,    # location_lat (обработанный)
                    location_lon,    # location_lon (обработанный)
                    row[10],         # metadata
                    received_at      # received_at (как строка)
                ]

                batch.append(raw_data)
                count += 1

                # Пакетная вставка каждые 100 записей
                if len(batch) >= 100:
                    client.execute(raw_query, batch)
                    batch = []

            # Вставка оставшихся записей
            if batch:
                client.execute(raw_query, batch)

            logging.info(f"✅ Loaded {count} raw telemetry records")
            total_loaded = total_loaded + count

        # Загрузка обработанных сессий
        CSV_PROCESS_FILE_PATH = 'data/telemetry_processed_data.csv'
        with open(CSV_PROCESS_FILE_PATH, 'r') as csvfile:
            csvreader = csv.reader(csvfile)

            process_query = """
                INSERT INTO telemetry.processed_data
                (
                    device_id, user_id, session_id, start_time, end_time, duration_minutes, movement_count,
                    avg_pressure, max_pressure, battery_consumed, anomalies, quality_score, created_at
                )
                VALUES
            """

            # Генерим запросы
            is_header = True
            count = 0
            batch = []
            for row in csvreader:
                if is_header:
                    is_header = False
                    continue

                # Преобразуем строки в datetime объекты
                start_time = execution_date - timedelta(days=1)
                end_time = start_time + timedelta(minutes=random.randint(1, 5))
                created_at = datetime.now()

                # Обработка массива anomalies (из строки в список)
                anomalies_str = row[10].strip()
                if anomalies_str and anomalies_str != '[]':
                    # Убираем скобки и разбиваем по запятым
                    anomalies_list = [item.strip().strip('"') for item in anomalies_str[1:-1].split(',') if item.strip()]
                else:
                    anomalies_list = []

                process_data = [
                    row[0],          # device_id
                    row[1],          # user_id
                    row[2],          # session_id
                    start_time,      # start_time (как строка)
                    end_time,        # end_time (как строка)
                    float(row[5]),   # duration_minutes
                    int(row[6]),     # movement_count
                    float(row[7]),   # avg_pressure
                    float(row[8]),   # max_pressure
                    float(row[9]),   # battery_consumed
                    anomalies_list,  # anomalies (как список)
                    float(row[11]),  # quality_score
                    created_at       # created_at (как строка)
                ]

                batch.append(process_data)
                count += 1

                # Пакетная вставка каждые 100 записей
                if len(batch) >= 100:
                    client.execute(process_query, batch)
                    batch = []

            # Вставка оставшихся записей
            if batch:
                client.execute(process_query, batch)

            logging.info(f"✅ Loaded {count} processed sessions")
            total_loaded = total_loaded + count

        # Логирование в аудит
        audit_data = (
            str(uuid.uuid4()),                              # operation_id
            kwargs['dag'].dag_id,                           # dag_id
            kwargs['task'].task_id,                         # task_id
            None,                                           # user_id
            'TELEMETRY_LOAD',                               # operation_type
            'telemetry.raw_data,telemetry.processed_data',  # table_name
            total_loaded,                                   # records_processed
            datetime.now(),                                 # start_time
            datetime.now(),                                 # end_time
            'SUCCESS',                                      # status
            None,                                           # error_message
            '',                                             # data_checksum
            ['GDPR_COMPLIANT', 'REAL_TIME'],                # compliance_flags (массив!)
            datetime.now(),                                 # created_at (лишнее, если default)
        )

        client.execute(audit_query, [audit_data])

        logging.info(f"🎯 Telemetry data loaded successfully. Total records: {total_loaded}")
        return total_loaded
    except Exception as e:
        logging.error(f"❌ Failed to load telemetry data to ClickHouse: {e}")
        # Логирование ошибки в аудит
        try:
            audit_data = (
                str(uuid.uuid4()),                              # operation_id
                kwargs['dag'].dag_id,                           # dag_id
                kwargs['task'].task_id,                         # task_id
                None,                                           # user_id
                'TELEMETRY_LOAD_ERROR',                         # operation_type
                'telemetry.raw_data,telemetry.processed_data',  # table_name
                0,                                              # records_processed
                datetime.now(),                                 # start_time
                datetime.now(),                                 # end_time
                'FAILED',                                       # status
                '{str(e)[:500]}',                               # error_message
                '',                                             # data_checksum
                ['ERROR'],                                      # compliance_flags (массив!)
                datetime.now(),                                 # created_at (лишнее, если default)
            )

            client.execute(audit_query, [audit_data])
        except:
            pass
        raise

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАДАЧ
# =====================================================

start = EmptyOperator(task_id='start_telemetry_processing', dag=dag)

# Загрузка в ClickHouse
load_data = PythonOperator(
    task_id='load_telemetry_to_clickhouse',
    python_callable=load_telemetry_to_clickhouse,
    op_kwargs={'ds': '{{ ds }}'},  # или '{{ execution_date }}'
    dag=dag
)

end = EmptyOperator(task_id='telemetry_processing_completed', dag=dag)

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# =====================================================

start >> load_data >> end