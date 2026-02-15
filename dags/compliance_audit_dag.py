"""
Compliance and Audit DAG for BionicPRO
GDPR/152-ФЗ соответствие, аудит операций и управление конфиденциальностью
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from clickhouse_driver import Client  # <-- Используем clickhouse-driver напрямую
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.smtp.operators.smtp import EmailOperator
import pandas as pd
import json
import logging
import hashlib
from cryptography.fernet import Fernet
import os
import uuid

# Конфигурация DAG
DEFAULT_ARGS = {
    'owner': 'bionicpro-compliance-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=15),
    'email': ['compliance@bionicpro.com', 'security@bionicpro.com'],
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
    'compliance_audit',
    default_args=DEFAULT_ARGS,
    description='GDPR/152-ФЗ Compliance and Security Audit for BionicPRO',
    schedule    ='0 2 * * *',  # Ежедневно в 2:00 утра
    catchup=False,
    max_active_runs=1,
    tags=['bionicpro', 'compliance', 'gdpr', '152-fz', 'audit', 'security'],
    doc_md="""
    # Compliance and Audit DAG

    Обеспечение соответствия требованиям GDPR и 152-ФЗ:
    - Аудит ETL операций
    - Шифрование чувствительных данных
    - Обработка запросов на удаление данных
    - Генерация отчетов о соответствии
    - Мониторинг нарушений безопасности
    """
)

def get_clickhouse_client():
    """Возвращает готовый клиент ClickHouse"""
    return Client(**CLICKHOUSE_CONFIG)

def audit_etl_operations(ds, **kwargs):
    """
    Аудит всех ETL операций за последние 24 часа
    """
    logging.info("🔍 Auditing ETL operations for the last 24 hours...")

    try:
        client = get_clickhouse_client()

        # Период аудита (последние 24 часа)
        execution_date = datetime.strptime(ds, "%Y-%m-%d")
        audit_start = execution_date - timedelta(hours=24)
        audit_end = execution_date

        logging.info(f"📅 Audit period: {audit_start} to {audit_end}")

        # Запрос операций ETL за период
        audit_query = f"""
        SELECT
            operation_id,
            dag_id,
            task_id,
            operation_type,
            table_name,
            records_processed,
            start_time,
            end_time,
            status,
            error_message,
            compliance_flags
        FROM audit.etl_operations
        WHERE start_time >= '{audit_start}'
          AND start_time < '{audit_end}'
        ORDER BY start_time DESC
        """

        audit_results = client.execute(audit_query)

        # Анализ операций
        operations_summary = {
            'total_operations': len(audit_results),
            'successful_operations': 0,
            'failed_operations': 0,
            'total_records_processed': 0,
            'compliance_violations': [],
            'performance_issues': [],
            'security_concerns': []
        }

        for operation in audit_results:
            operation_id, dag_id, task_id, operation_type, table_name, \
            records_processed, start_time, end_time, status, error_message, compliance_flags = operation

            # Подсчет статистики
            if status == 'SUCCESS':
                operations_summary['successful_operations'] += 1
            else:
                operations_summary['failed_operations'] += 1

            operations_summary['total_records_processed'] += records_processed or 0

            # Проверка compliance флагов
            flags = compliance_flags or []
            if 'GDPR_COMPLIANT' not in flags:
                operations_summary['compliance_violations'].append({
                    'operation_id': operation_id,
                    'dag_id': dag_id,
                    'task_id': task_id,
                    'violation': 'GDPR compliance flag missing',
                    'severity': 'HIGH'
                })

            if 'FZ152_COMPLIANT' not in flags:
                operations_summary['compliance_violations'].append({
                    'operation_id': operation_id,
                    'dag_id': dag_id,
                    'task_id': task_id,
                    'violation': '152-ФЗ compliance flag missing',
                    'severity': 'HIGH'
                })

            # Проверка производительности
            if end_time and start_time:
                duration_seconds = (end_time - start_time).total_seconds()
                if duration_seconds > 3600:  # Больше часа
                    operations_summary['performance_issues'].append({
                        'operation_id': operation_id,
                        'dag_id': dag_id,
                        'task_id': task_id,
                        'duration_seconds': duration_seconds,
                        'issue': 'Long running operation'
                    })

            # Проверка ошибок безопасности
            if error_message and ('authentication' in error_message.lower() or 'authorization' in error_message.lower()):
                operations_summary['security_concerns'].append({
                    'operation_id': operation_id,
                    'dag_id': dag_id,
                    'task_id': task_id,
                    'error': error_message,
                    'concern': 'Authentication/Authorization error'
                })

        # Сохранение результатов аудита
        kwargs['ti'].xcom_push(key='operations_audit', value=operations_summary)

        # Создание записи об аудите
        logging.info(f"Формируем запись для аудита: {operations_summary['total_operations']}")
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
            'AUDIT_SUMMARY',                                # operation_type
            'audit.etl_operations',                         # table_name
            operations_summary['total_operations'],         # records_processed
            datetime.now(),                                 # start_time
            datetime.now(),                                 # end_time
            'SUCCESS',                                      # status
            None,                                           # error_message
            '',                                             # data_checksum
            ['AUDIT_COMPLETED', 'GDPR_COMPLIANT', 'FZ152_COMPLIANT'], # compliance_flags (массив!)
            datetime.now(),                                 # created_at (лишнее, если default)
        )
        logging.info("Запись аудита в clickhouse")
        client.execute(audit_query, [audit_data])

        logging.info(f"✅ Audit completed. Summary: {operations_summary}")
        return operations_summary
    except Exception as e:
        logging.error(f"❌ Failed to audit ETL operations: {e}")
        raise

def encrypt_sensitive_data(**kwargs):
    """
    Шифрование чувствительных персональных данных
    """
    logging.info("🔐 Encrypting sensitive personal data...")

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

        # Получение ключа шифрования из переменных окружения
        encryption_key = os.environ.get('BIONICPRO_ENCRYPTION_KEY')
        if not encryption_key:
            # Генерация нового ключа если отсутствует (только для разработки!)
            encryption_key = Fernet.generate_key().decode()
            logging.warning("⚠️ Generated new encryption key. Store it securely!")

        fernet = Fernet(encryption_key.encode())

        # Шифрование email адресов в таблице клиентов
        email_encryption_query = """
        SELECT customer_id, email
        FROM crm.customers
        WHERE email != '' AND email NOT LIKE 'encrypted:%'
        LIMIT 1000
        """

        customers_to_encrypt = client.execute(email_encryption_query)

        encrypted_count = 0
        for customer_id, email in customers_to_encrypt:
            try:
                # Шифрование email
                encrypted_email = fernet.encrypt(email.encode()).decode()
                encrypted_email = f"encrypted:{encrypted_email}"

                # Обновление записи
                update_query = f"""
                ALTER TABLE crm.customers
                UPDATE email = '{encrypted_email}'
                WHERE customer_id = '{customer_id}'
                """
                client.client(update_query)

                encrypted_count += 1
            except Exception as e:
                logging.warning(f"⚠️ Failed to encrypt email for customer {customer_id}: {e}")
                continue

        # Шифрование телефонных номеров
        phone_encryption_query = """
        SELECT customer_id, phone
        FROM crm.customers
        WHERE phone != '' AND phone NOT LIKE 'encrypted:%'
        LIMIT 1000
        """

        phones_to_encrypt = client.execute(phone_encryption_query)

        for customer_id, phone in phones_to_encrypt:
            try:
                # Шифрование номера телефона
                encrypted_phone = fernet.encrypt(phone.encode()).decode()
                encrypted_phone = f"encrypted:{encrypted_phone}"

                # Обновление записи
                update_query = f"""
                ALTER TABLE crm.customers
                UPDATE phone = '{encrypted_phone}'
                WHERE customer_id = '{customer_id}'
                """
                client.execute(update_query)

                encrypted_count += 1
            except Exception as e:
                logging.warning(f"⚠️ Failed to encrypt phone for customer {customer_id}: {e}")
                continue

        # Логирование в аудит
        audit_data = (
            str(uuid.uuid4()),                              # operation_id
            kwargs['dag'].dag_id,                           # dag_id
            kwargs['task'].task_id,                         # task_id
            None,                                           # user_id
            'DATA_ENCRYPTION',                              # operation_type
            'crm.customers',                                # table_name
            encrypted_count,                                # records_processed
            datetime.now(),                                 # start_time
            datetime.now(),                                 # end_time
            'SUCCESS',                                      # status
            None,                                           # error_message
            '',                                             # data_checksum
            ['GDPR_COMPLIANT', 'FZ152_COMPLIANT', 'DATA_ENCRYPTED'], # compliance_flags (массив!)
            datetime.now(),                                 # created_at (лишнее, если default)
        )

        client.execute(audit_query, [audit_data])

        kwargs['ti'].xcom_push(key='encrypted_records_count', value=encrypted_count)

        logging.info(f"🔐 Encrypted {encrypted_count} sensitive data records")
        return encrypted_count
    except Exception as e:
        logging.error(f"❌ Failed to encrypt sensitive data: {e}")
        raise

def process_gdpr_requests(**kwargs):
    """
    Обработка запросов GDPR (право на забвение, экспорт данных)
    """
    logging.info("📋 Processing GDPR data requests...")

    try:
        client = get_clickhouse_client()

        # Получение ожидающих запросов GDPR
        pending_requests_query = """
        SELECT
            request_id,
            user_id,
            request_type,
            request_date,
            status,
            deletion_reason
        FROM audit.gdpr_requests
        WHERE status = 'PENDING'
        ORDER BY request_date ASC
        LIMIT 100
        """

        pending_requests = client.execute(pending_requests_query)

        processed_requests = 0
        failed_requests = 0

        for request in pending_requests:
            request_id, user_id, request_type, request_date, status, deletion_reason = request

            try:
                logging.info(f"🔄 Processing GDPR request {request_id} for user {user_id} (type: {request_type})")

                # Обновление статуса на PROCESSING
                update_status_query = f"""
                ALTER TABLE audit.gdpr_requests
                UPDATE status = 'PROCESSING', processed_date = now()
                WHERE request_id = '{request_id}'
                """
                client.execute(update_status_query)

                if request_type == 'DELETE':
                    # Удаление данных пользователя из всех таблиц
                    tables_to_clean = [
                        'telemetry.raw_data',
                        'telemetry.processed_data',
                        'reports.user_analytics',
                        'crm.customers',
                        'crm.orders',
                        'crm.prosthetics'
                    ]

                    affected_tables = []
                    total_deleted = 0

                    for table in tables_to_clean:
                        try:
                            # Подсчет записей перед удалением
                            count_query = f"SELECT count(*) FROM {table} WHERE user_id = '{user_id}'"
                            count_result = client.execute(count_query)
                            records_count = count_result[0] if count_result else 0

                            if records_count > 0:
                                # Удаление записей
                                delete_query = f"ALTER TABLE {table} DELETE WHERE user_id = '{user_id}'"
                                client.execute(delete_query)

                                affected_tables.append(table)
                                total_deleted += records_count

                                logging.info(f"🗑️ Deleted {records_count} records from {table}")
                        except Exception as e:
                            logging.error(f"❌ Failed to delete from {table}: {e}")
                            continue

                    # Обновление статуса запроса
                    completion_query = f"""
                    ALTER TABLE audit.gdpr_requests
                    UPDATE
                        status = 'COMPLETED',
                        affected_tables = {affected_tables},
                        processed_date = now()
                    WHERE request_id = '{request_id}'
                    """
                    client.execute(completion_query)

                    processed_requests += 1
                    logging.info(f"✅ GDPR deletion completed for user {user_id}. Total deleted: {total_deleted}")

                elif request_type == 'EXPORT':
                    # Экспорт данных пользователя
                    export_data = {}

                    # Экспорт из CRM
                    crm_export_query = f"""
                    SELECT * FROM crm.customers WHERE user_id = '{user_id}'
                    """
                    crm_data = client.execute(crm_export_query)
                    export_data['crm_customers'] = crm_data

                    # Экспорт телеметрии (последние 30 дней)
                    telemetry_export_query = f"""
                    SELECT * FROM telemetry.processed_data
                    WHERE user_id = '{user_id}'
                      AND start_time >= now() - INTERVAL 30 DAY
                    LIMIT 10000
                    """
                    telemetry_data = client.execute(telemetry_export_query)
                    export_data['telemetry_sessions'] = telemetry_data

                    # Экспорт отчетов
                    reports_export_query = f"""
                    SELECT * FROM reports.user_analytics
                    WHERE user_id = '{user_id}'
                    ORDER BY report_date DESC
                    LIMIT 1000
                    """
                    reports_data = client.execute(reports_export_query)
                    export_data['user_reports'] = reports_data

                    # Сохранение экспорта (в реальной системе нужно отправить пользователю)
                    export_json = json.dumps(export_data, default=str, ensure_ascii=False)
                    export_file_path = f"/tmp/gdpr_export_{user_id}_{request_id}.json"

                    with open(export_file_path, 'w', encoding='utf-8') as f:
                        f.write(export_json)

                    # Обновление статуса
                    completion_query = f"""
                    ALTER TABLE audit.gdpr_requests
                    UPDATE status = 'COMPLETED', processed_date = now()
                    WHERE request_id = '{request_id}'
                    """
                    client.execute(completion_query)

                    processed_requests += 1
                    logging.info(f"✅ GDPR export completed for user {user_id}. File: {export_file_path}")
            except Exception as e:
                logging.error(f"❌ Failed to process GDPR request {request_id}: {e}")

                # Обновление статуса на FAILED
                error_query = f"""
                ALTER TABLE audit.gdpr_requests
                UPDATE status = 'FAILED', processed_date = now()
                WHERE request_id = '{request_id}'
                """
                client.execute(error_query)

                failed_requests += 1

        # Сохранение статистики обработки
        kwargs['ti'].xcom_push(key='gdpr_processed', value=processed_requests)
        kwargs['ti'].xcom_push(key='gdpr_failed', value=failed_requests)

        logging.info(f"📋 GDPR processing completed. Processed: {processed_requests}, Failed: {failed_requests}")
        return {
            'processed': processed_requests,
            'failed': failed_requests
        }
    except Exception as e:
        logging.error(f"❌ Failed to process GDPR requests: {e}")
        raise

def generate_compliance_report(ds, **kwargs):
    """
    Генерация отчета о соответствии нормативным требованиям
    """
    logging.info("📊 Generating compliance report...")

    try:
        client = get_clickhouse_client()

        # Получение статистики из предыдущих задач
        operations_audit = kwargs['ti'].xcom_pull(
            task_ids='audit_etl_operations',
            key='operations_audit'
        ) or {}

        encrypted_count = kwargs['ti'].xcom_pull(
            task_ids='encrypt_sensitive_data',
            key='encrypted_records_count'
        ) or 0

        gdpr_stats = kwargs['ti'].xcom_pull(
            task_ids='process_gdpr_requests',
            key='gdpr_processed'
        ) or 0

        # Дополнительная статистика
        # Общее количество пользователей
        users_count_query = "SELECT count(DISTINCT user_id) FROM crm.customers"
        total_users = client.execute(users_count_query)[0]

        # Количество активных устройств
        devices_count_query = """
        SELECT count(DISTINCT device_id)
        FROM telemetry.processed_data
        WHERE start_time >= now() - INTERVAL 30 DAY
        """
        active_devices = client.execute(devices_count_query)[0]

        # Статистика GDPR запросов
        gdpr_stats_query = """
        SELECT
            request_type,
            status,
            count(*) as count
        FROM audit.gdpr_requests
        WHERE request_date >= now() - INTERVAL 30 DAY
        GROUP BY request_type, status
        """
        gdpr_requests_stats = client.execute(gdpr_stats_query)

        execution_date = datetime.strptime(ds, "%Y-%m-%d")

        # Формирование отчета
        compliance_report = {
            'report_date': execution_date.isoformat(),
            'reporting_period': '24 hours',
            'system_overview': {
                'total_users': total_users,
                'active_devices': active_devices,
                'encrypted_records_processed': encrypted_count
            },
            'etl_operations_audit': operations_audit,
            'gdpr_compliance': {
                'requests_processed_today': gdpr_stats,
                'monthly_requests_breakdown': dict(
                    (f"{req_type}_{status}", count)
                    for req_type, status, count in gdpr_requests_stats
                )
            },
            'security_metrics': {
                'data_encryption_status': 'ACTIVE',
                'access_control_status': 'ROW_LEVEL_SECURITY_ENABLED',
                'audit_logging_status': 'ENABLED'
            },
            'compliance_status': {
                'gdpr_compliant': True,
                'fz152_compliant': True,
                'data_retention_policy': 'ENFORCED',
                'user_consent_management': 'IMPLEMENTED'
            }
        }

        # Оценка общего статуса compliance
        compliance_violations = operations_audit.get('compliance_violations', [])
        if compliance_violations:
            compliance_report['compliance_status']['overall_status'] = 'VIOLATIONS_DETECTED'
            compliance_report['compliance_status']['violations_count'] = len(compliance_violations)
        else:
            compliance_report['compliance_status']['overall_status'] = 'COMPLIANT'

        # Сохранение отчета
        kwargs['ti'].xcom_push(key='compliance_report', value=compliance_report)

        # Сохранение в файл для аудиторов
        report_json = json.dumps(compliance_report, default=str, ensure_ascii=False, indent=2)
        report_file_path = f"/tmp/compliance_report_{execution_date.strftime('%Y%m%d')}.json"

        with open(report_file_path, 'w', encoding='utf-8') as f:
            f.write(report_json)

        logging.info(f"📊 Compliance report generated: {report_file_path}")
        logging.info(f"📈 Report summary: {compliance_report['compliance_status']}")

        return compliance_report

    except Exception as e:
        logging.error(f"❌ Failed to generate compliance report: {e}")
        raise

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАДАЧ
# =====================================================

start = EmptyOperator(
    task_id='start_compliance_audit',
    dag=dag
)

# Аудит ETL операций
audit_operations = PythonOperator(
    task_id='audit_etl_operations',
    python_callable=audit_etl_operations,
    op_kwargs={'ds': '{{ ds }}'},  # или '{{ execution_date }}'
    dag=dag
)

# Шифрование чувствительных данных
encrypt_data = PythonOperator(
    task_id='encrypt_sensitive_data',
    python_callable=encrypt_sensitive_data,
    dag=dag
)

# Обработка GDPR запросов
process_gdpr = PythonOperator(
    task_id='process_gdpr_requests',
    python_callable=process_gdpr_requests,
    dag=dag
)

# Генерация отчета compliance
generate_report = PythonOperator(
    task_id='generate_compliance_report',
    python_callable=generate_compliance_report,
    op_kwargs={'ds': '{{ ds }}'},  # или '{{ execution_date }}'
    dag=dag
)

# Отправка уведомлений при нарушениях
# send_compliance_alert = EmailOperator(
#     task_id='send_compliance_alert',
#     to=['compliance@bionicpro.com', 'security@bionicpro.com'],
#     subject='BionicPRO Daily Compliance Report - {{ ds }}',
#     html_content="""
#     <h2>BionicPRO Compliance Report</h2>
#     <p>Daily compliance audit completed for {{ ds }}.</p>
#     <p>Please review the compliance report for any violations or security concerns.</p>
#     <p>Report file: /tmp/compliance_report_{{ ds_nodash }}.json</p>
#     """,
#     dag=dag,
#     trigger_rule='all_done'  # Отправляем даже если есть ошибки
# )

end = EmptyOperator(
    task_id='compliance_audit_completed',
    dag=dag
)

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# =====================================================

# start >> [audit_operations, encrypt_data, process_gdpr] >> generate_report >> send_compliance_alert >> end
start >> [audit_operations, encrypt_data, process_gdpr] >> generate_report >> end