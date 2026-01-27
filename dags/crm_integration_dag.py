"""
CRM Integration DAG for BionicPRO
Интеграция с Битрикс24 CRM для извлечения данных клиентов, заказов и протезов
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.clickhouse.hooks.clickhouse import ClickHouseHook
from airflow.models import Variable
import pandas as pd
import json
import logging

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

# Создание DAG
dag = DAG(
    'crm_integration',
    default_args=DEFAULT_ARGS,
    description='Битрикс24 CRM Integration for BionicPRO',
    schedule_interval=None,  # Запускается из master DAG
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

def extract_customers_from_bitrix(**context):
    """
    Извлечение данных клиентов из Битрикс24
    """
    logging.info("🔄 Extracting customers from Битрикс24...")

    try:
        # Подключение к Битрикс24 API
        http_hook = HttpHook(http_conn_id='bitrix24_api')

        # Получение последней отметки времени для инкрементальной загрузки
        last_sync = context['task_instance'].xcom_pull(
            dag_id='crm_integration',
            task_ids='get_last_sync_timestamp',
            key='last_customer_sync'
        )

        if last_sync:
            # Инкрементальная загрузка
            filter_param = f"&filter[><DATE_CREATE]={last_sync}"
            logging.info(f"📅 Incremental load from: {last_sync}")
        else:
            # Полная загрузка при первом запуске
            filter_param = ""
            logging.info("📁 Full load - first run")

        # Запрос к API контактов
        customers_response = http_hook.run(
            endpoint=f'crm.contact.list?select[]=ID&select[]=NAME&select[]=SECOND_NAME&select[]=EMAIL&select[]=PHONE&select[]=DATE_CREATE&select[]=DATE_MODIFY{filter_param}',
            headers={'Content-Type': 'application/json'}
        )

        if customers_response.status_code != 200:
            raise Exception(f"Битрикс24 API error: {customers_response.status_code}")

        customers_data = customers_response.json()

        # Обработка данных
        processed_customers = []
        for contact in customers_data.get('result', []):
            processed_customers.append({
                'customer_id': f"crm_{contact['ID']}",
                'user_id': f"user_{contact['ID']}",  # Связка с системой аутентификации
                'first_name': contact.get('NAME', ''),
                'last_name': contact.get('SECOND_NAME', ''),
                'email': contact.get('EMAIL', [{}])[0].get('VALUE', '') if contact.get('EMAIL') else '',
                'phone': contact.get('PHONE', [{}])[0].get('VALUE', '') if contact.get('PHONE') else '',
                'region': 'RU',  # По умолчанию Россия
                'registration_date': contact.get('DATE_CREATE', ''),
                'status': 'ACTIVE',
                'bitrix_contact_id': contact['ID']
            })

        # Сохранение в XCom для следующих задач
        context['task_instance'].xcom_push(key='customers_data', value=processed_customers)

        logging.info(f"✅ Extracted {len(processed_customers)} customers from Битрикс24")
        return len(processed_customers)

    except Exception as e:
        logging.error(f"❌ Failed to extract customers from Битрикс24: {e}")
        raise

def extract_orders_from_bitrix(**context):
    """
    Извлечение заказов и сделок из Битрикс24
    """
    logging.info("🔄 Extracting orders from Битрикс24...")

    try:
        http_hook = HttpHook(http_conn_id='bitrix24_api')

        # Инкрементальная загрузка
        last_sync = context['task_instance'].xcom_pull(
            dag_id='crm_integration',
            task_ids='get_last_sync_timestamp',
            key='last_order_sync'
        )

        filter_param = f"&filter[><DATE_CREATE]={last_sync}" if last_sync else ""

        # Запрос к API сделок
        deals_response = http_hook.run(
            endpoint=f'crm.deal.list?select[]=ID&select[]=CONTACT_ID&select[]=TITLE&select[]=OPPORTUNITY&select[]=STAGE_ID&select[]=DATE_CREATE&select[]=CLOSEDATE{filter_param}',
            headers={'Content-Type': 'application/json'}
        )

        if deals_response.status_code != 200:
            raise Exception(f"Битрикс24 API error: {deals_response.status_code}")

        deals_data = deals_response.json()

        # Обработка заказов
        processed_orders = []
        for deal in deals_data.get('result', []):
            processed_orders.append({
                'order_id': f"order_{deal['ID']}",
                'customer_id': f"crm_{deal.get('CONTACT_ID', '')}",
                'user_id': f"user_{deal.get('CONTACT_ID', '')}",
                'prosthetic_type': deal.get('TITLE', 'Unknown'),
                'order_date': deal.get('DATE_CREATE', ''),
                'delivery_date': deal.get('CLOSEDATE', None),
                'status': deal.get('STAGE_ID', 'NEW'),
                'price': float(deal.get('OPPORTUNITY', 0) or 0),
                'bitrix_deal_id': deal['ID']
            })

        context['task_instance'].xcom_push(key='orders_data', value=processed_orders)

        logging.info(f"✅ Extracted {len(processed_orders)} orders from Битрикс24")
        return len(processed_orders)

    except Exception as e:
        logging.error(f"❌ Failed to extract orders from Битрикс24: {e}")
        raise

def load_crm_data_to_clickhouse(**context):
    """
    Загрузка данных CRM в ClickHouse
    """
    logging.info("🔄 Loading CRM data to ClickHouse...")

    try:
        clickhouse_hook = ClickHouseHook()

        # Получение данных из предыдущих задач
        customers_data = context['task_instance'].xcom_pull(
            task_ids='extract_customers_from_bitrix',
            key='customers_data'
        )
        orders_data = context['task_instance'].xcom_pull(
            task_ids='extract_orders_from_bitrix',
            key='orders_data'
        )

        total_loaded = 0

        # Загрузка клиентов
        if customers_data:
            customers_df = pd.DataFrame(customers_data)

            # Подготовка данных для вставки
            customers_values = []
            for _, row in customers_df.iterrows():
                customers_values.append(
                    f"('{row['customer_id']}', '{row['user_id']}', '{row['first_name']}', "
                    f"'{row['last_name']}', '{row['email']}', '{row['phone']}', "
                    f"'{row['region']}', '{row['registration_date']}', '{row['status']}', "
                    f"'{row['bitrix_contact_id']}', now(), now())"
                )

            if customers_values:
                # Вставка с обновлением (UPSERT)
                customers_query = f"""
                INSERT INTO crm.customers
                (customer_id, user_id, first_name, last_name, email, phone,
                 region, registration_date, status, bitrix_contact_id, created_at, updated_at)
                VALUES {', '.join(customers_values)}
                """

                clickhouse_hook.run(customers_query)
                total_loaded += len(customers_values)
                logging.info(f"✅ Loaded {len(customers_values)} customers to ClickHouse")

        # Загрузка заказов
        if orders_data:
            orders_df = pd.DataFrame(orders_data)

            orders_values = []
            for _, row in orders_df.iterrows():
                delivery_date = f"'{row['delivery_date']}'" if row['delivery_date'] else 'NULL'
                orders_values.append(
                    f"('{row['order_id']}', '{row['customer_id']}', '{row['user_id']}', "
                    f"'{row['prosthetic_type']}', '{row['order_date']}', {delivery_date}, "
                    f"'{row['status']}', {row['price']}, '{row['bitrix_deal_id']}', now())"
                )

            if orders_values:
                orders_query = f"""
                INSERT INTO crm.orders
                (order_id, customer_id, user_id, prosthetic_type, order_date,
                 delivery_date, status, price, bitrix_deal_id, created_at)
                VALUES {', '.join(orders_values)}
                """

                clickhouse_hook.run(orders_query)
                total_loaded += len(orders_values)
                logging.info(f"✅ Loaded {len(orders_values)} orders to ClickHouse")

        # Логирование в аудит
        audit_query = f"""
        INSERT INTO audit.etl_operations
        VALUES (
            generateUUIDv4(),
            '{context['dag'].dag_id}',
            '{context['task'].task_id}',
            null,
            'CRM_LOAD',
            'crm.customers,crm.orders',
            {total_loaded},
            now(),
            now(),
            'SUCCESS',
            null,
            '',
            ['GDPR_COMPLIANT', 'FZ152_COMPLIANT']
        )
        """
        clickhouse_hook.run(audit_query)

        logging.info(f"🎯 CRM data loaded successfully. Total records: {total_loaded}")
        return total_loaded

    except Exception as e:
        logging.error(f"❌ Failed to load CRM data to ClickHouse: {e}")
        # Логирование ошибки в аудит
        try:
            error_audit_query = f"""
            INSERT INTO audit.etl_operations
            VALUES (
                generateUUIDv4(),
                '{context['dag'].dag_id}',
                '{context['task'].task_id}',
                null,
                'CRM_LOAD_ERROR',
                'crm.customers,crm.orders',
                0,
                now(),
                now(),
                'FAILED',
                '{str(e)[:500]}',
                '',
                ['ERROR']
            )
            """
            clickhouse_hook.run(error_audit_query)
        except:
            pass
        raise

def get_last_sync_timestamp(**context):
    """
    Получение последней отметки времени синхронизации для инкрементальной загрузки
    """
    try:
        clickhouse_hook = ClickHouseHook()

        # Последняя синхронизация клиентов
        customer_sync_query = """
        SELECT max(updated_at) as last_sync
        FROM crm.customers
        WHERE created_at >= today() - INTERVAL 7 DAY
        """
        customer_result = clickhouse_hook.get_first(customer_sync_query)
        last_customer_sync = customer_result[0] if customer_result and customer_result[0] else None

        # Последняя синхронизация заказов
        order_sync_query = """
        SELECT max(created_at) as last_sync
        FROM crm.orders
        WHERE created_at >= today() - INTERVAL 7 DAY
        """
        order_result = clickhouse_hook.get_first(order_sync_query)
        last_order_sync = order_result[0] if order_result and order_result[0] else None

        # Сохранение в XCom
        context['task_instance'].xcom_push(key='last_customer_sync', value=str(last_customer_sync) if last_customer_sync else None)
        context['task_instance'].xcom_push(key='last_order_sync', value=str(last_order_sync) if last_order_sync else None)

        logging.info(f"📅 Last customer sync: {last_customer_sync}")
        logging.info(f"📅 Last order sync: {last_order_sync}")

        return {
            'last_customer_sync': last_customer_sync,
            'last_order_sync': last_order_sync
        }

    except Exception as e:
        logging.warning(f"⚠️ Could not get last sync timestamp: {e}")
        # При первом запуске или ошибке делаем полную загрузку
        return {
            'last_customer_sync': None,
            'last_order_sync': None
        }

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАДАЧ
# =====================================================

start = DummyOperator(
    task_id='start_crm_integration',
    dag=dag
)

# Получение последней отметки синхронизации
get_last_sync = PythonOperator(
    task_id='get_last_sync_timestamp',
    python_callable=get_last_sync_timestamp,
    dag=dag
)

# Извлечение клиентов
extract_customers = PythonOperator(
    task_id='extract_customers_from_bitrix',
    python_callable=extract_customers_from_bitrix,
    dag=dag
)

# Извлечение заказов
extract_orders = PythonOperator(
    task_id='extract_orders_from_bitrix',
    python_callable=extract_orders_from_bitrix,
    dag=dag
)

# Загрузка в ClickHouse
load_to_clickhouse = PythonOperator(
    task_id='load_crm_data_to_clickhouse',
    python_callable=load_crm_data_to_clickhouse,
    dag=dag
)

end = DummyOperator(
    task_id='crm_integration_completed',
    dag=dag
)

# =====================================================
# ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# =====================================================

start >> get_last_sync >> [extract_customers, extract_orders] >> load_to_clickhouse >> end