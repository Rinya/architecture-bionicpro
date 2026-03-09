from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import logging
from clickhouse_driver import Client

default_args = {
    'start_date': datetime(2024, 1, 1),
    'catchup': False
}

logger = logging.getLogger(__name__)

def test_clickhouse():
    print("Начинаю проверку соединения с ClickHouse (через clickhouse_driver)")
    logging.info("Начинаю проверку соединения с ClickHouse (через clickhouse_driver)")
    try:
        client = Client(
            host='clickhouse',
            user='reports_user',
            password='secure_reports_password_2024!',
            database='reports',  # если нужно поменять базу
            port=9000  # или другой порт если не стандартный
        )
        result = client.execute('SELECT 1')
        logging.info(f"Результат запроса: {result}")
    except Exception as e:
        logging.error(f"Ошибка при подключении или выполнении запроса: {e}")
        raise

with DAG(
    dag_id='test_clickhouse_driver_conn_logging',
    default_args=default_args,
    schedule=None,
    description='Test ClickHouse connection with clickhouse_driver and logging',
) as dag:
    test_conn = PythonOperator(
        task_id='test_clickhouse_conn_python',
        python_callable=test_clickhouse
    )