"""
Telemetry Processing DAG for BionicPRO
Обработка потоковых данных телеметрии от ESP32 протезов через Kafka
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.clickhouse.hooks.clickhouse import ClickHouseHook
from kafka import KafkaConsumer
import json
import logging
import pandas as pd
from typing import List, Dict, Any
import uuid

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

# Создание DAG
dag = DAG(
    'telemetry_processing',
    default_args=DEFAULT_ARGS,
    description='ESP32 Telemetry Processing for BionicPRO',
    schedule_interval=None,  # Запускается из master DAG
    catchup=False,
    max_active_runs=2,  # Допускаем параллельное выполнение
    tags=['bionicpro', 'telemetry', 'esp32', 'kafka', 'real-time'],
    doc_md="""
    # ESP32 Telemetry Processing DAG

    Обработка потоковых данных телеметрии от бионических протезов:
    - Чтение данных из Kafka
    - Валидация и очистка данных
    - Обогащение пользовательскими данными
    - Создание сессий использования
    - Загрузка в ClickHouse
    """
)

# Конфигурация Kafka
KAFKA_CONFIG = {
    'bootstrap_servers': ['kafka:9092'],
    'group_id': 'bionicpro-telemetry-consumer',
    'auto_offset_reset': 'latest',  # Читаем только новые сообщения
    'enable_auto_commit': True,
    'consumer_timeout_ms': 30000,  # 30 секунд таймаут
    'max_poll_records': 1000,  # Максимум записей за раз
}

def consume_telemetry_from_kafka(**context):
    """
    Чтение потоковых данных телеметрии из Kafka
    """
    logging.info("📡 Starting telemetry consumption from Kafka...")

    try:
        # Создание Kafka consumer
        consumer = KafkaConsumer(
            'prosthetics-telemetry',
            **KAFKA_CONFIG,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )

        telemetry_messages = []
        message_count = 0

        # Чтение сообщений с таймаутом
        for message in consumer:
            try:
                telemetry_data = message.value

                # Базовая валидация структуры сообщения
                if not all(field in telemetry_data for field in ['device_id', 'timestamp', 'sensor_data']):
                    logging.warning(f"⚠️ Invalid message structure: {telemetry_data}")
                    continue

                telemetry_messages.append(telemetry_data)
                message_count += 1

                # Ограничение на количество сообщений за один раз
                if message_count >= 10000:
                    logging.info(f"📊 Reached batch limit: {message_count} messages")
                    break

            except json.JSONDecodeError as e:
                logging.warning(f"⚠️ Failed to decode message: {e}")
                continue
            except Exception as e:
                logging.warning(f"⚠️ Error processing message: {e}")
                continue

        consumer.close()

        # Сохранение данных в XCom
        context['task_instance'].xcom_push(key='raw_telemetry', value=telemetry_messages)

        logging.info(f"✅ Consumed {len(telemetry_messages)} telemetry messages from Kafka")
        return len(telemetry_messages)

    except Exception as e:
        logging.error(f"❌ Failed to consume from Kafka: {e}")
        raise

def validate_and_clean_telemetry(**context):
    """
    Валидация и очистка данных телеметрии
    """
    logging.info("🧹 Validating and cleaning telemetry data...")

    try:
        # Получение данных из предыдущей задачи
        raw_telemetry = context['task_instance'].xcom_pull(
            task_ids='consume_telemetry_from_kafka',
            key='raw_telemetry'
        )

        if not raw_telemetry:
            logging.info("📭 No telemetry data to process")
            return 0

        validated_records = []

        for record in raw_telemetry:
            try:
                # Валидация обязательных полей
                if not record.get('device_id'):
                    continue

                # Парсинг sensor_data
                sensor_data = record.get('sensor_data', {})

                # Создание нормализованных записей для каждого сенсора
                for sensor_type, sensor_value in sensor_data.items():
                    if sensor_type in ['pressure', 'acceleration', 'gyroscope', 'temperature']:
                        validated_record = {
                            'device_id': record['device_id'],
                            'user_id': f"device_{record['device_id']}", # Связка с пользователем
                            'timestamp': record['timestamp'],
                            'sensor_type': sensor_type,
                            'sensor_value': float(sensor_value),
                            'battery_level': float(record.get('battery_level', 0)),
                            'signal_strength': int(record.get('signal_strength', -100)),
                            'firmware_version': record.get('firmware_version', '1.0.0'),
                            'location_lat': record.get('location', {}).get('lat'),
                            'location_lon': record.get('location', {}).get('lon'),
                            'metadata': json.dumps(record.get('metadata', {}))
                        }

                        # Дополнительная валидация значений
                        if self._validate_sensor_ranges(sensor_type, sensor_value):
                            validated_records.append(validated_record)

            except (ValueError, TypeError, KeyError) as e:
                logging.warning(f"⚠️ Invalid record skipped: {e}")
                continue

        # Сохранение валидированных данных
        context['task_instance'].xcom_push(key='validated_telemetry', value=validated_records)

        logging.info(f"✅ Validated {len(validated_records)} telemetry records")
        return len(validated_records)

    except Exception as e:
        logging.error(f"❌ Failed to validate telemetry data: {e}")
        raise

def _validate_sensor_ranges(sensor_type: str, value: float) -> bool:
    """
    Валидация диапазонов значений сенсоров
    """
    ranges = {
        'pressure': (0, 1000),      # Давление в условных единицах
        'acceleration': (-50, 50),   # Ускорение в м/с²
        'gyroscope': (-360, 360),    # Угловая скорость в град/с
        'temperature': (-10, 60),    # Температура в °C
    }

    if sensor_type in ranges:
        min_val, max_val = ranges[sensor_type]
        return min_val <= value <= max_val

    return True

def enrich_with_user_data(**context):
    """
    Обогащение телеметрии данными пользователей из CRM
    """
    logging.info("🔗 Enriching telemetry with user data...")

    try:
        clickhouse_hook = ClickHouseHook()

        # Получение валидированных данных
        validated_telemetry = context['task_instance'].xcom_pull(
            task_ids='validate_and_clean_telemetry',
            key='validated_telemetry'
        )

        if not validated_telemetry:
            logging.info("📭 No validated telemetry data to enrich")
            return 0

        # Получение уникальных device_id для поиска пользователей
        device_ids = list(set(record['device_id'] for record in validated_telemetry))

        # Запрос связки device_id -> user_id из CRM
        device_user_mapping = {}
        if device_ids:
            device_ids_str = "','".join(device_ids)
            mapping_query = f"""
            SELECT device_serial, user_id
            FROM crm.prosthetics
            WHERE device_serial IN ('{device_ids_str}')
            AND status = 'ACTIVE'
            """

            mapping_results = clickhouse_hook.get_records(mapping_query)
            device_user_mapping = {device_serial: user_id for device_serial, user_id in mapping_results}

        # Обогащение записей
        enriched_records = []
        for record in validated_telemetry:
            # Обновление user_id если есть связка в CRM
            if record['device_id'] in device_user_mapping:
                record['user_id'] = device_user_mapping[record['device_id']]

            enriched_records.append(record)

        # Сохранение обогащенных данных
        context['task_instance'].xcom_push(key='enriched_telemetry', value=enriched_records)

        logging.info(f"✅ Enriched {len(enriched_records)} telemetry records")
        logging.info(f"🔗 Found user mapping for {len(device_user_mapping)} devices")

        return len(enriched_records)

    except Exception as e:
        logging.error(f"❌ Failed to enrich telemetry data: {e}")
        raise

def create_usage_sessions(**context):
    """
    Создание сессий использования протеза из потока телеметрии
    """
    logging.info("🎮 Creating usage sessions from telemetry...")

    try:
        # Получение обогащенных данных
        enriched_telemetry = context['task_instance'].xcom_pull(
            task_ids='enrich_with_user_data',
            key='enriched_telemetry'
        )

        if not enriched_telemetry:
            logging.info("📭 No enriched telemetry data to process")
            return 0

        # Группировка по device_id и временным интервалам
        df = pd.DataFrame(enriched_telemetry)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(['device_id', 'timestamp'])

        sessions = []

        # Обработка каждого устройства отдельно
        for device_id in df['device_id'].unique():
            device_data = df[df['device_id'] == device_id].copy()

            # Выявление сессий (разрыв более 5 минут = новая сессия)
            device_data['time_diff'] = device_data['timestamp'].diff()
            session_breaks = device_data['time_diff'] > pd.Timedelta(minutes=5)
            device_data['session_id'] = session_breaks.cumsum()

            # Создание сессий
            for session_id in device_data['session_id'].unique():
                session_data = device_data[device_data['session_id'] == session_id]

                if len(session_data) < 5:  # Минимум 5 измерений для сессии
                    continue

                # Расчет метрик сессии
                start_time = session_data['timestamp'].min()
                end_time = session_data['timestamp'].max()
                duration_minutes = (end_time - start_time).total_seconds() / 60

                # Анализ движений (на основе pressure сенсора)
                pressure_data = session_data[session_data['sensor_type'] == 'pressure']
                movement_count = len(pressure_data[pressure_data['sensor_value'] > 50])  # Пороговое значение

                # Расчет средних значений
                avg_pressure = pressure_data['sensor_value'].mean() if not pressure_data.empty else 0
                max_pressure = pressure_data['sensor_value'].max() if not pressure_data.empty else 0

                # Потребление батареи
                battery_start = session_data['battery_level'].iloc[0]
                battery_end = session_data['battery_level'].iloc[-1]
                battery_consumed = max(0, battery_start - battery_end)

                # Выявление аномалий
                anomalies = []
                if max_pressure > 800:  # Критическое давление
                    anomalies.append('HIGH_PRESSURE')
                if battery_consumed > 20:  # Большой расход батареи
                    anomalies.append('HIGH_BATTERY_CONSUMPTION')
                if duration_minutes < 1:  # Очень короткая сессия
                    anomalies.append('SHORT_SESSION')

                # Оценка качества сессии
                quality_score = self._calculate_quality_score(
                    duration_minutes, movement_count, avg_pressure, len(anomalies)
                )

                session = {
                    'device_id': device_id,
                    'user_id': session_data['user_id'].iloc[0],
                    'session_id': f"{device_id}_{start_time.strftime('%Y%m%d_%H%M%S')}",
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_minutes': round(duration_minutes, 2),
                    'movement_count': movement_count,
                    'avg_pressure': round(avg_pressure, 2),
                    'max_pressure': round(max_pressure, 2),
                    'battery_consumed': round(battery_consumed, 2),
                    'anomalies': anomalies,
                    'quality_score': round(quality_score, 2)
                }

                sessions.append(session)

        # Сохранение сессий
        context['task_instance'].xcom_push(key='usage_sessions', value=sessions)

        logging.info(f"✅ Created {len(sessions)} usage sessions")
        return len(sessions)

    except Exception as e:
        logging.error(f"❌ Failed to create usage sessions: {e}")
        raise

def _calculate_quality_score(duration: float, movements: int, avg_pressure: float, anomaly_count: int) -> float:
    """
    Расчет оценки качества сессии использования
    """
    base_score = 100.0

    # Штрафы за различные проблемы
    if duration < 5:  # Слишком короткая сессия
        base_score -= 30
    elif duration < 15:
        base_score -= 10

    if movements < 10:  # Низкая активность
        base_score -= 20

    if avg_pressure < 20:  # Низкое давление (плохой контакт)
        base_score -= 25

    # Штраф за аномалии
    base_score -= anomaly_count * 15

    return max(0, min(100, base_score))

def load_telemetry_to_clickhouse(**context):
    """
    Загрузка обработанной телеметрии в ClickHouse
    """
    logging.info("💾 Loading telemetry data to ClickHouse...")

    try:
        clickhouse_hook = ClickHouseHook()

        # Получение данных из предыдущих задач
        enriched_telemetry = context['task_instance'].xcom_pull(
            task_ids='enrich_with_user_data',
            key='enriched_telemetry'
        )
        usage_sessions = context['task_instance'].xcom_pull(
            task_ids='create_usage_sessions',
            key='usage_sessions'
        )

        total_loaded = 0

        # Загрузка сырых данных телеметрии
        if enriched_telemetry:
            # Пакетная вставка сырых данных
            raw_values = []
            for record in enriched_telemetry:
                lat_val = f"'{record['location_lat']}'" if record['location_lat'] else 'NULL'
                lon_val = f"'{record['location_lon']}'" if record['location_lon'] else 'NULL'

                raw_values.append(
                    f"('{record['device_id']}', '{record['user_id']}', '{record['timestamp']}', "
                    f"'{record['sensor_type']}', {record['sensor_value']}, {record['battery_level']}, "
                    f"{record['signal_strength']}, '{record['firmware_version']}', {lat_val}, {lon_val}, "
                    f"'{record['metadata']}', now())"
                )

            if raw_values:
                # Батчевая вставка по 1000 записей
                batch_size = 1000
                for i in range(0, len(raw_values), batch_size):
                    batch = raw_values[i:i + batch_size]
                    raw_query = f"""
                    INSERT INTO telemetry.raw_data
                    (device_id, user_id, timestamp, sensor_type, sensor_value, battery_level,
                     signal_strength, firmware_version, location_lat, location_lon, metadata, received_at)
                    VALUES {', '.join(batch)}
                    """
                    clickhouse_hook.run(raw_query)

                total_loaded += len(raw_values)
                logging.info(f"✅ Loaded {len(raw_values)} raw telemetry records")

        # Загрузка обработанных сессий
        if usage_sessions:
            session_values = []
            for session in usage_sessions:
                anomalies_array = "'" + "','".join(session['anomalies']) + "'" if session['anomalies'] else ""

                session_values.append(
                    f"('{session['device_id']}', '{session['user_id']}', '{session['session_id']}', "
                    f"'{session['start_time']}', '{session['end_time']}', {session['duration_minutes']}, "
                    f"{session['movement_count']}, {session['avg_pressure']}, {session['max_pressure']}, "
                    f"{session['battery_consumed']}, [{anomalies_array}], {session['quality_score']}, now())"
                )

            if session_values:
                sessions_query = f"""
                INSERT INTO telemetry.processed_data
                (device_id, user_id, session_id, start_time, end_time, duration_minutes,
                 movement_count, avg_pressure, max_pressure, battery_consumed, anomalies, quality_score, created_at)
                VALUES {', '.join(session_values)}
                """
                clickhouse_hook.run(sessions_query)

                total_loaded += len(session_values)
                logging.info(f"✅ Loaded {len(session_values)} processed sessions")

        # Логирование в аудит
        audit_query = f"""
        INSERT INTO audit.etl_operations
        VALUES (
            generateUUIDv4(),
            '{context['dag'].dag_id}',
            '{context['task'].task_id}',
            null,
            'TELEMETRY_LOAD',
            'telemetry.raw_data,telemetry.processed_data',
            {total_loaded},
            now(),
            now(),
            'SUCCESS',
            null,
            '',
            ['GDPR_COMPLIANT', 'REAL_TIME']
        )
        """
        clickhouse_hook.run(audit_query)

        logging.info(f"🎯 Telemetry data loaded successfully. Total records: {total_loaded}")
        return total_loaded

    except Exception as e:
        logging.error(f"❌ Failed to load telemetry data to ClickHouse: {e}")
        raise

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАДАЧ
# =====================================================

start = DummyOperator(
    task_id='start_telemetry_processing',
    dag=dag
)

# Чтение из Kafka
consume_kafka = PythonOperator(
    task_id='consume_telemetry_from_kafka',
    python_callable=consume_telemetry_from_kafka,
    dag=dag
)

# Валидация данных
validate_data = PythonOperator(
    task_id='validate_and_clean_telemetry',
    python_callable=validate_and_clean_telemetry,
    dag=dag
)

# Обогащение пользователями
enrich_data = PythonOperator(
    task_id='enrich_with_user_data',
    python_callable=enrich_with_user_data,
    dag=dag
)

# Создание сессий
create_sessions = PythonOperator(
    task_id='create_usage_sessions',
    python_callable=create_usage_sessions,
    dag=dag
)

# Загрузка в ClickHouse
load_data = PythonOperator(
    task_id='load_telemetry_to_clickhouse',
    python_callable=load_telemetry_to_clickhouse,
    dag=dag
)

end = DummyOperator(
    task_id='telemetry_processing_completed',
    dag=dag
)

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# =====================================================

start >> consume_kafka >> validate_data >> enrich_data >> create_sessions >> load_data >> end