"""
Reports Mart DAG for BionicPRO
Создание витрины данных для пользовательских отчетов
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.clickhouse.hooks.clickhouse import ClickHouseHook
from airflow.providers.redis.hooks.redis_hook import RedisHook
import pandas as pd
import json
import logging

# Конфигурация DAG
DEFAULT_ARGS = {
    'owner': 'bionicpro-reports-team',
    'depends_on_past': True,  # Зависит от предыдущих запусков
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
}

# Создание DAG
dag = DAG(
    'reports_mart',
    default_args=DEFAULT_ARGS,
    description='Reports Data Mart Creation for BionicPRO',
    schedule_interval=None,  # Запускается из master DAG
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

def aggregate_daily_telemetry(**context):
    """
    Агрегация телеметрии по дням для каждого пользователя
    """
    logging.info("📊 Aggregating daily telemetry data...")

    try:
        clickhouse_hook = ClickHouseHook()

        # Определение диапазона дат для обработки
        execution_date = context['execution_date']
        start_date = execution_date - timedelta(days=1)  # Вчерашний день
        end_date = execution_date

        logging.info(f"📅 Processing data for date range: {start_date.date()} to {end_date.date()}")

        # Запрос агрегации телеметрии по дням
        telemetry_agg_query = f"""
        SELECT
            user_id,
            device_id,
            toDate(start_time) as report_date,

            -- Общее время использования
            sum(duration_minutes) / 60 as daily_usage_hours,

            -- Эффективность движений (средняя оценка качества)
            avg(quality_score) as movement_efficiency,

            -- Здоровье батареи (среднее потребление)
            avg(battery_consumed) as avg_battery_consumption,

            -- Количество аномалий
            sum(length(anomalies)) as anomaly_count,

            -- Общее количество сессий
            count(*) as total_sessions,

            -- Средняя продолжительность сессии
            avg(duration_minutes) as avg_session_duration,

            -- Максимальное давление за день
            max(max_pressure) as max_pressure_reached,

            -- Последняя синхронизация
            max(start_time) as last_sync

        FROM telemetry.processed_data
        WHERE toDate(start_time) >= '{start_date.date()}'
          AND toDate(start_time) < '{end_date.date()}'
        GROUP BY user_id, device_id, report_date
        HAVING daily_usage_hours > 0  -- Исключаем дни без использования
        ORDER BY user_id, device_id, report_date
        """

        # Выполнение запроса
        telemetry_results = clickhouse_hook.get_records(telemetry_agg_query)

        # Преобразование в структурированный формат
        aggregated_data = []
        for row in telemetry_results:
            user_id, device_id, report_date, daily_usage_hours, movement_efficiency, \
            avg_battery_consumption, anomaly_count, total_sessions, avg_session_duration, \
            max_pressure_reached, last_sync = row

            # Расчет maintenance score на основе давления и использования
            maintenance_score = self._calculate_maintenance_score(
                daily_usage_hours, max_pressure_reached, avg_battery_consumption
            )

            # Здоровье батареи (инвертированное потребление)
            battery_health = max(0, 100 - (avg_battery_consumption * 5))

            aggregated_data.append({
                'user_id': user_id,
                'device_id': device_id,
                'report_date': report_date,
                'daily_usage_hours': round(daily_usage_hours, 2),
                'movement_efficiency': round(movement_efficiency, 2),
                'maintenance_score': round(maintenance_score, 2),
                'battery_health': round(battery_health, 2),
                'anomaly_count': int(anomaly_count),
                'total_sessions': int(total_sessions),
                'avg_session_duration': round(avg_session_duration, 2),
                'max_pressure_reached': round(max_pressure_reached, 2),
                'last_sync': last_sync
            })

        # Сохранение результатов в XCom
        context['task_instance'].xcom_push(key='daily_aggregates', value=aggregated_data)

        logging.info(f"✅ Aggregated {len(aggregated_data)} daily telemetry records")
        return len(aggregated_data)

    except Exception as e:
        logging.error(f"❌ Failed to aggregate daily telemetry: {e}")
        raise

def _calculate_maintenance_score(usage_hours: float, max_pressure: float, battery_consumption: float) -> float:
    """
    Расчет оценки состояния протеза для maintenance
    """
    base_score = 100.0

    # Штрафы за превышение нормальных параметров
    if max_pressure > 600:  # Высокое давление
        base_score -= 30
    elif max_pressure > 400:
        base_score -= 10

    if battery_consumption > 15:  # Высокое потребление батареи
        base_score -= 20
    elif battery_consumption > 10:
        base_score -= 10

    if usage_hours > 12:  # Интенсивное использование
        base_score -= 15
    elif usage_hours > 8:
        base_score -= 5

    return max(0, min(100, base_score))

def enrich_with_crm_data(**context):
    """
    Обогащение агрегированных данных информацией из CRM
    """
    logging.info("🔗 Enriching telemetry aggregates with CRM data...")

    try:
        clickhouse_hook = ClickHouseHook()

        # Получение агрегированных данных
        daily_aggregates = context['task_instance'].xcom_pull(
            task_ids='aggregate_daily_telemetry',
            key='daily_aggregates'
        )

        if not daily_aggregates:
            logging.info("📭 No daily aggregates to enrich")
            return 0

        # Получение уникальных user_id для поиска в CRM
        user_ids = list(set(record['user_id'] for record in daily_aggregates))

        # Запрос данных пользователей из CRM
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

            crm_results = clickhouse_hook.get_records(crm_query)

            # Группировка CRM данных по user_id
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

        # Обогащение данных
        enriched_data = []
        for record in daily_aggregates:
            user_id = record['user_id']
            device_id = record['device_id']

            # Добавление CRM информации
            if user_id in crm_data:
                user_info = crm_data[user_id]
                record['user_first_name'] = user_info['first_name']
                record['user_last_name'] = user_info['last_name']
                record['user_email'] = user_info['email']
                record['user_region'] = user_info['region']

                # Поиск информации о конкретном протезе
                prosthetic_info = None
                for prosthetic in user_info['prosthetics']:
                    if prosthetic['device_serial'] == device_id:
                        prosthetic_info = prosthetic
                        break

                if prosthetic_info:
                    record['prosthetic_model'] = prosthetic_info['model']
                    record['activation_date'] = prosthetic_info['activation_date']
                    record['warranty_expiry'] = prosthetic_info['warranty_expiry']

                    # Расчет дней до истечения гарантии
                    if prosthetic_info['warranty_expiry']:
                        warranty_date = datetime.strptime(str(prosthetic_info['warranty_expiry']), '%Y-%m-%d %H:%M:%S')
                        days_to_warranty_expiry = (warranty_date - datetime.now()).days
                        record['warranty_days_remaining'] = max(0, days_to_warranty_expiry)
                    else:
                        record['warranty_days_remaining'] = 0

            enriched_data.append(record)

        # Сохранение обогащенных данных
        context['task_instance'].xcom_push(key='enriched_reports', value=enriched_data)

        logging.info(f"✅ Enriched {len(enriched_data)} records with CRM data")
        logging.info(f"🔗 Found CRM data for {len(crm_data)} users")

        return len(enriched_data)

    except Exception as e:
        logging.error(f"❌ Failed to enrich with CRM data: {e}")
        raise

def load_reports_mart(**context):
    """
    Загрузка готовой витрины отчетов в ClickHouse
    """
    logging.info("💾 Loading reports mart to ClickHouse...")

    try:
        clickhouse_hook = ClickHouseHook()

        # Получение обогащенных данных
        enriched_reports = context['task_instance'].xcom_pull(
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
            # Upsert операция (замена существующих записей)
            # Сначала удаляем существующие записи за этот день
            execution_date = context['execution_date']
            delete_date = (execution_date - timedelta(days=1)).date()

            delete_query = f"""
            ALTER TABLE reports.user_analytics DELETE
            WHERE toDate(report_date) = '{delete_date}'
            """
            clickhouse_hook.run(delete_query)

            # Вставка новых данных
            insert_query = f"""
            INSERT INTO reports.user_analytics
            (user_id, device_id, report_date, daily_usage_hours, movement_efficiency,
             maintenance_score, battery_health, anomaly_count, total_sessions,
             avg_session_duration, max_pressure_reached, last_sync, created_at)
            VALUES {', '.join(report_values)}
            """
            clickhouse_hook.run(insert_query)

            logging.info(f"✅ Loaded {len(report_values)} reports to mart")

        # Логирование в аудит
        audit_query = f"""
        INSERT INTO audit.etl_operations
        VALUES (
            generateUUIDv4(),
            '{context['dag'].dag_id}',
            '{context['task'].task_id}',
            null,
            'REPORTS_MART_LOAD',
            'reports.user_analytics',
            {len(enriched_reports)},
            now(),
            now(),
            'SUCCESS',
            null,
            '',
            ['GDPR_COMPLIANT', 'REPORTS_READY']
        )
        """
        clickhouse_hook.run(audit_query)

        context['task_instance'].xcom_push(key='loaded_reports_count', value=len(enriched_reports))

        return len(enriched_reports)

    except Exception as e:
        logging.error(f"❌ Failed to load reports mart: {e}")
        raise

def cache_popular_reports(**context):
    """
    Кеширование популярных отчетов в Redis для быстрого доступа API
    """
    logging.info("🚀 Caching popular reports in Redis...")

    try:
        redis_hook = RedisHook(redis_conn_id='redis_default')
        clickhouse_hook = ClickHouseHook()

        # Получение количества загруженных отчетов
        loaded_count = context['task_instance'].xcom_pull(
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
        LIMIT 1000  -- Кешируем только топ-1000 активных пользователей
        """

        cache_results = clickhouse_hook.get_records(cache_query)

        cached_count = 0
        for user_id, device_id, reports_json in cache_results:
            try:
                # Создание ключа кеша
                cache_key = f"user_report:{user_id}:{device_id}"

                # Подготовка данных для кеша
                cache_data = {
                    'user_id': user_id,
                    'device_id': device_id,
                    'reports': reports_json,
                    'cached_at': datetime.now().isoformat(),
                    'cache_version': 'v1.0'
                }

                # Сохранение в Redis с TTL 6 часов
                redis_hook.set_key(
                    cache_key,
                    json.dumps(cache_data),
                    ttl=21600  # 6 часов в секундах
                )

                cached_count += 1

            except Exception as e:
                logging.warning(f"⚠️ Failed to cache report for {user_id}:{device_id}: {e}")
                continue

        # Кеширование агрегированной статистики
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

            stats_result = clickhouse_hook.get_first(stats_query)
            if stats_result:
                total_reports, active_users, avg_usage_hours, avg_efficiency = stats_result

                stats_data = {
                    'total_reports': total_reports,
                    'active_users': active_users,
                    'avg_usage_hours': round(avg_usage_hours, 2),
                    'avg_efficiency': round(avg_efficiency, 2),
                    'generated_at': datetime.now().isoformat()
                }

                redis_hook.set_key(
                    'reports:statistics:weekly',
                    json.dumps(stats_data),
                    ttl=3600  # 1 час
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

start = DummyOperator(
    task_id='start_reports_mart',
    dag=dag
)

# Агрегация телеметрии по дням
aggregate_telemetry = PythonOperator(
    task_id='aggregate_daily_telemetry',
    python_callable=aggregate_daily_telemetry,
    dag=dag
)

# Обогащение данными CRM
enrich_crm = PythonOperator(
    task_id='enrich_with_crm_data',
    python_callable=enrich_with_crm_data,
    dag=dag
)

# Загрузка в витрину
load_mart = PythonOperator(
    task_id='load_reports_mart',
    python_callable=load_reports_mart,
    dag=dag
)

# Кеширование в Redis
cache_reports = PythonOperator(
    task_id='cache_popular_reports',
    python_callable=cache_popular_reports,
    dag=dag
)

end = DummyOperator(
    task_id='reports_mart_completed',
    dag=dag
)

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# =====================================================

start >> aggregate_telemetry >> enrich_crm >> load_mart >> cache_reports >> end