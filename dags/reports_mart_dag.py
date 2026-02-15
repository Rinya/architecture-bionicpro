"""
Reports Mart DAG for BionicPRO
Создание витрины данных для пользовательских отчетов
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.redis.hooks.redis import RedisHook
from clickhouse_driver import Client  # <-- Используем clickhouse-driver напрямую
import pandas as pd
import json
import logging
import uuid

# Конфигурация DAG
DEFAULT_ARGS = {
    'owner': 'bionicpro-reports-team',
    'depends_on_past': True,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
    'execution_timeout': timedelta(minutes=30),  # Увеличиваем timeout
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
    'reports_mart',
    default_args=DEFAULT_ARGS,
    description='Reports Data Mart Creation for BionicPRO',
    schedule=None,  # Запускается из master DAG
    catchup=False,
    max_active_runs=1,
    tags=['bionicpro', 'reports', 'mart', 'analytics'],
    doc_md="""
    # Reports Data Mart DAG

    Создание витрины данных для пользовательских отчетов:
    - Агрегация данных телеметрии по пользователям
    - Объединение с данными CRM
    - Расчет KPI и метрик
    - Кеширование отчетов для API
    """
)

def get_clickhouse_client():
    """Возвращает готовый клиент ClickHouse"""
    return Client(**CLICKHOUSE_CONFIG)

def aggregate_daily_telemetry(ds, **kwargs):
    """
    Агрегация телеметрии по дням для каждого пользователя.
    ds -- str "YYYY-MM-DD"
    """
    logging.info("📊 Aggregating daily telemetry data...")
    from datetime import datetime, timedelta

    try:
        client = get_clickhouse_client()
        execution_date = datetime.strptime(ds, "%Y-%m-%d")
        start_date = execution_date - timedelta(days=1)
        end_date = execution_date
        logging.info(f"📅 Processing data for date range: {start_date.date()} to {end_date.date()}")

        telemetry_agg_query = f"""
        SELECT
            user_id,
            device_id,
            toDate(start_time) as report_date,
            sum(duration_minutes) / 60 as daily_usage_hours,
            avg(quality_score) as movement_efficiency,
            avg(battery_consumed) as avg_battery_consumption,
            sum(length(anomalies)) as anomaly_count,
            count(*) as total_sessions,
            avg(duration_minutes) as avg_session_duration,
            max(max_pressure) as max_pressure_reached,
            max(start_time) as last_sync
        FROM telemetry.processed_data
        WHERE toDate(start_time) >= '{start_date.date()}'
          AND toDate(start_time) < '{end_date.date()}'
          AND duration_minutes > 0
        GROUP BY user_id, device_id, report_date
        HAVING daily_usage_hours > 0
        ORDER BY user_id, device_id, report_date
        LIMIT 10000
        """

        logging.info(f"🔍 Executing telemetry aggregation query for {start_date.date()} to {end_date.date()}")
        telemetry_results = client.execute(telemetry_agg_query)
        logging.info(f"📊 Retrieved {len(telemetry_results)} telemetry aggregation rows")

        def safe_float(value, default=0.0):
            try:
                if value is None:
                    return default
                result = float(value)
                if result != result or result == float('inf') or result == float('-inf'):
                    return default
                return result
            except (ValueError, TypeError):
                return default

        def safe_round(value, precision=2, default=0.0):
            safe_val = safe_float(value, default)
            return round(safe_val, precision)

        aggregated_data = []
        batch_size = 1000
        total_rows = len(telemetry_results)

        for i, row in enumerate(telemetry_results):
            user_id, device_id, report_date, daily_usage_hours, movement_efficiency, \
            avg_battery_consumption, anomaly_count, total_sessions, avg_session_duration, \
            max_pressure_reached, last_sync = row

            safe_daily_usage = safe_float(daily_usage_hours)
            safe_movement_efficiency = safe_float(movement_efficiency)
            safe_battery_consumption = safe_float(avg_battery_consumption)
            safe_max_pressure = safe_float(max_pressure_reached)

            maintenance_score = _calculate_maintenance_score(
                safe_daily_usage, safe_max_pressure, safe_battery_consumption
            )
            battery_health = max(0, 100 - (safe_battery_consumption * 5))

            aggregated_data.append({
                'user_id': user_id,
                'device_id': device_id,
                'report_date': report_date,
                'daily_usage_hours': safe_round(safe_daily_usage, 2),
                'movement_efficiency': safe_round(safe_movement_efficiency, 2),
                'maintenance_score': safe_round(maintenance_score, 2),
                'battery_health': safe_round(battery_health, 2),
                'anomaly_count': int(anomaly_count or 0),
                'total_sessions': int(total_sessions or 0),
                'avg_session_duration': safe_round(avg_session_duration, 2),
                'max_pressure_reached': safe_round(safe_max_pressure, 2),
                'last_sync': last_sync
            })
            if (i + 1) % batch_size == 0:
                logging.info(f"⚡ Processed {i + 1}/{total_rows} rows ({((i + 1)/total_rows*100):.1f}%)")

        kwargs['ti'].xcom_push(key='daily_aggregates', value=aggregated_data)
        logging.info(f"✅ Aggregated {len(aggregated_data)} daily telemetry records")
        return len(aggregated_data)
    except Exception as e:
        logging.error(f"❌ Failed to aggregate daily telemetry: {e}")
        raise

def _calculate_maintenance_score(usage_hours: float, max_pressure: float, battery_consumption: float) -> float:
    """
    Расчет оценки состояния протеза для maintenance
    """
    # Защита от NaN значений
    def safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            result = float(value)
            if result != result or result == float('inf') or result == float('-inf'):  # NaN check
                return default
            return result
        except (ValueError, TypeError):
            return default

    # Безопасное преобразование входных параметров
    safe_usage = safe_float(usage_hours)
    safe_pressure = safe_float(max_pressure)
    safe_battery = safe_float(battery_consumption)

    base_score = 100.0

    if safe_pressure > 600:
        base_score -= 30
    elif safe_pressure > 400:
        base_score -= 10

    if safe_battery > 15:
        base_score -= 20
    elif safe_battery > 10:
        base_score -= 10

    if safe_usage > 12:
        base_score -= 15
    elif safe_usage > 8:
        base_score -= 5

    return max(0, min(100, base_score))

def enrich_with_crm_data(**kwargs):
    """
    Обогащение агрегированных данных информацией из CRM
    """
    logging.info("🔗 Enriching telemetry aggregates with CRM data...")

    try:
        client = get_clickhouse_client()

        # Получение агрегированных данных
        daily_aggregates = kwargs['ti'].xcom_pull(
            task_ids='aggregate_daily_telemetry',
            key='daily_aggregates'
        )

        if not daily_aggregates:
            logging.info("📭 No daily aggregates to enrich")
            return 0

        user_ids = list(set(record['user_id'] for record in daily_aggregates))

        crm_data = {}
        if user_ids:
            user_ids_str = "','".join(user_ids)
            crm_query = f"""
            SELECT
                c.user_id,
                c.first_name,
                c.last_name,
                c.email,
                c.region,
                c.registration_date,
                p.prosthetic_id,
                p.device_serial,
                p.model,
                p.activation_date,
                p.warranty_expiry
            FROM crm.customers c
            LEFT JOIN crm.prosthetics p ON c.user_id = p.user_id
            WHERE c.user_id IN ('{user_ids_str}')
              AND p.status = 'ACTIVE'
            """

            crm_results = client.execute(crm_query)

            for row in crm_results:
                user_id, first_name, last_name, email, region, registration_date, \
                prosthetic_id, device_serial, model, activation_date, warranty_expiry = row

                if user_id not in crm_data:
                    crm_data[user_id] = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'region': region,
                        'registration_date': registration_date,
                        'prosthetics': []
                    }

                if prosthetic_id:
                    crm_data[user_id]['prosthetics'].append({
                        'prosthetic_id': prosthetic_id,
                        'device_serial': device_serial,
                        'model': model,
                        'activation_date': activation_date,
                        'warranty_expiry': warranty_expiry
                    })

        enriched_data = []
        for record in daily_aggregates:
            user_id = record['user_id']
            device_id = record['device_id']

            if user_id in crm_data:
                user_info = crm_data[user_id]
                record['user_first_name'] = user_info['first_name']
                record['user_last_name'] = user_info['last_name']
                record['user_email'] = user_info['email']
                record['user_region'] = user_info['region']

                prosthetic_info = None
                for prosthetic in user_info['prosthetics']:
                    if prosthetic['device_serial'] == device_id:
                        prosthetic_info = prosthetic
                        break

                if prosthetic_info:
                    record['prosthetic_model'] = prosthetic_info['model']
                    record['activation_date'] = prosthetic_info['activation_date']
                    record['warranty_expiry'] = prosthetic_info['warranty_expiry']

                    if prosthetic_info['warranty_expiry']:
                        warranty_date = datetime.strptime(str(prosthetic_info['warranty_expiry']), '%Y-%m-%d %H:%M:%S')
                        days_to_warranty_expiry = (warranty_date - datetime.now()).days
                        record['warranty_days_remaining'] = max(0, days_to_warranty_expiry)
                    else:
                        record['warranty_days_remaining'] = 0

            enriched_data.append(record)

        kwargs['ti'].xcom_push(key='enriched_reports', value=enriched_data)

        logging.info(f"✅ Enriched {len(enriched_data)} records with CRM data")
        logging.info(f"🔗 Found CRM data for {len(crm_data)} users")

        return len(enriched_data)
    except Exception as e:
        logging.error(f"❌ Failed to enrich with CRM data: {e}")
        raise

def load_reports_mart(ds, **kwargs):
    """
    Загрузка готовой витрины отчетов в ClickHouse
    """
    logging.info("💾 Loading reports mart to ClickHouse...")

    try:
        client = get_clickhouse_client()

        enriched_reports = kwargs['ti'].xcom_pull(
            task_ids='enrich_with_crm_data',
            key='enriched_reports'
        )

        if not enriched_reports:
            logging.info("📭 No enriched reports to load")
            return 0

        # Подготовка данных для вставки
        report_values = []
        for record in enriched_reports:
            report_values.append(
                f"('{record['user_id']}', '{record['device_id']}', '{record['report_date']}', "
                f"{record['daily_usage_hours']}, {record['movement_efficiency']}, "
                f"{record['maintenance_score']}, {record['battery_health']}, "
                f"{record['anomaly_count']}, {record['total_sessions']}, "
                f"{record['avg_session_duration']}, {record['max_pressure_reached']}, "
                f"'{record['last_sync']}', now())"
            )

        if report_values:
            # Удаление старых записей за день
            execution_date = datetime.strptime(ds, "%Y-%m-%d")
            delete_date = (execution_date - timedelta(days=1)).date()

            delete_query = f"""
            ALTER TABLE reports.user_analytics DELETE
            WHERE toDate(report_date) = '{delete_date}'
            """
            client.execute(delete_query)

            # Вставка новых данных
            insert_query = f"""
            INSERT INTO reports.user_analytics
            (user_id, device_id, report_date, daily_usage_hours, movement_efficiency,
             maintenance_score, battery_health, anomaly_count, total_sessions,
             avg_session_duration, max_pressure_reached, last_sync, created_at)
            VALUES {', '.join(report_values)}
            """
            client.execute(insert_query)

            logging.info(f"✅ Loaded {len(report_values)} reports to mart")

        # Аудит
        audit_query = """
            INSERT INTO audit.etl_operations
            (
                operation_id, dag_id, task_id, user_id, operation_type, table_name,
                records_processed, start_time, end_time, status, error_message,
                data_checksum, compliance_flags, created_at
            )
            VALUES
        """

        audit_data = (
            str(uuid.uuid4()),                              # operation_id
            kwargs['dag'].dag_id,                           # dag_id
            kwargs['task'].task_id,                         # task_id
            None,                                           # user_id
            'REPORTS_MART_LOAD',                            # operation_type
            'reports.user_analytics',                       # table_name
            len(enriched_reports),                          # records_processed
            datetime.now(),                                 # start_time
            datetime.now(),                                 # end_time
            'SUCCESS',                                      # status
            None,                                           # error_message
            '',                                             # data_checksum
            ['GDPR_COMPLIANT', 'REPORTS_READY'],            # compliance_flags (массив!)
            datetime.now(),                                 # created_at (лишнее, если default)
        )

        client.execute(audit_query, [audit_data])

        kwargs['ti'].xcom_push(key='loaded_reports_count', value=len(enriched_reports))

        return len(enriched_reports)
    except Exception as e:
        logging.error(f"❌ Failed to load reports mart: {e}")
        raise

def cache_popular_reports(**kwargs):
    """
    Кеширование популярных отчетов в Redis для быстрого доступа API
    """
    logging.info("🚀 Caching popular reports in Redis...")

    try:
        redis_hook = RedisHook(redis_conn_id='redis_default')
        client = get_clickhouse_client()

        loaded_count = kwargs['ti'].xcom_pull(
            task_ids='load_reports_mart',
            key='loaded_reports_count'
        )

        if not loaded_count:
            logging.info("📭 No reports to cache")
            return 0

        # Запрос последних отчетов для кеширования
        cache_query = """
        SELECT
            user_id,
            device_id,
            groupArray((report_date, daily_usage_hours, movement_efficiency,
                       maintenance_score, battery_health, anomaly_count)) as reports_data
        FROM reports.user_analytics
        WHERE report_date >= today() - INTERVAL 30 DAY
        GROUP BY user_id, device_id
        ORDER BY user_id, device_id
        LIMIT 1000
        """

        cache_results = client.execute(cache_query)

        cached_count = 0
        for user_id, device_id, reports_json in cache_results:
            try:
                cache_key = f"user_report:{user_id}:{device_id}"

                cache_data = {
                    'user_id': user_id,
                    'device_id': device_id,
                    'reports': reports_json,
                    'cached_at': datetime.now().isoformat(),
                    'cache_version': 'v1.0'
                }

                redis_hook.set_key(
                    cache_key,
                    json.dumps(cache_data),
                    ttl=21600
                )

                cached_count += 1

            except Exception as e:
                logging.warning(f"⚠️ Failed to cache report for {user_id}:{device_id}: {e}")
                continue

        # Кеширование статистики
        try:
            stats_query = """
            SELECT
                count(*) as total_reports,
                uniq(user_id) as active_users,
                avg(daily_usage_hours) as avg_usage_hours,
                avg(movement_efficiency) as avg_efficiency
            FROM reports.user_analytics
            WHERE report_date >= today() - INTERVAL 7 DAY
            """

            stats_result = client.execute(stats_query)[0]
            total_reports, active_users, avg_usage_hours, avg_efficiency = stats_result

            # Функция для безопасной обработки значений
            def safe_round(value, precision=2, default=0.0):
                try:
                    if value is None:
                        return default
                    result = float(value)
                    if result != result or result == float('inf') or result == float('-inf'):  # NaN check
                        return default
                    return round(result, precision)
                except (ValueError, TypeError):
                    return default

            stats_data = {
                'total_reports': int(total_reports or 0),
                'active_users': int(active_users or 0),
                'avg_usage_hours': safe_round(avg_usage_hours),
                'avg_efficiency': safe_round(avg_efficiency),
                'generated_at': datetime.now().isoformat()
            }

            redis_hook.set_key(
                'reports:statistics:weekly',
                json.dumps(stats_data),
                ttl=3600
            )

            logging.info(f"📊 Cached weekly statistics: {stats_data}")

        except Exception as e:
            logging.warning(f"⚠️ Failed to cache statistics: {e}")

        logging.info(f"🎯 Cached {cached_count} user reports in Redis")
        return cached_count

    except Exception as e:
        logging.error(f"❌ Failed to cache reports in Redis: {e}")
        raise

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАДАЧ
# =====================================================

start = EmptyOperator(
    task_id='start_reports_mart',
    dag=dag
)

aggregate_telemetry = PythonOperator(
    task_id='aggregate_daily_telemetry',
    python_callable=aggregate_daily_telemetry,
    op_kwargs={'ds': '{{ ds }}'},  # или '{{ execution_date }}'
    dag=dag
)

enrich_crm = PythonOperator(
    task_id='enrich_with_crm_data',
    python_callable=enrich_with_crm_data,
    dag=dag
)

load_mart = PythonOperator(
    task_id='load_reports_mart',
    python_callable=load_reports_mart,
    op_kwargs={'ds': '{{ ds }}'},  # или '{{ execution_date }}'
    dag=dag
)

cache_reports = PythonOperator(
    task_id='cache_popular_reports',
    python_callable=cache_popular_reports,
    dag=dag
)

end = EmptyOperator(
    task_id='reports_mart_completed',
    dag=dag
)

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# =====================================================

start >> aggregate_telemetry >> enrich_crm >> load_mart >> cache_reports >> end
