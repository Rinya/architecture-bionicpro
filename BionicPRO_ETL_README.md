# BionicPRO ETL System

Система ETL для обработки данных телеметрии протезов и создания отчетов для пользователей.

## Архитектура

![ETL Architecture](./task3_etl.drawio)

Система состоит из следующих компонентов:

### Основные компоненты
- **Apache Airflow** - оркестрация ETL процессов
- **ClickHouse** - OLAP витрина данных
- **Kafka** - потоковая обработка данных от ESP32
- **Redis** - кеширование API ответов
- **PostgreSQL** - метаданные Airflow и пользователи

### Источники данных
- **Битрикс24 CRM** - данные клиентов и заказов
- **ESP32 протезы** - телеметрия в реальном времени
- **Keycloak** - данные пользователей и аутентификация

## Быстрый старт

### 1. Предварительные требования

```bash
# Docker и Docker Compose
docker --version
docker-compose --version

# Python 3.9+ (для разработки DAG)
python --version
```

### 2. Настройка окружения

```bash
# Клонирование проекта
cd architecture-bionicpro

# Создание директорий для Airflow
mkdir -p dags logs plugins sql

# Настройка прав доступа
export AIRFLOW_UID=50000
```

### 3. Запуск инфраструктуры

```bash
# Запуск всех сервисов
docker-compose -f airflow-docker-compose.yml up -d

# Проверка статуса сервисов
docker-compose -f airflow-docker-compose.yml ps
```

### 4. Доступ к веб-интерфейсам

- **Airflow UI**: http://localhost:8080 (admin/admin)
- **ClickHouse**: http://localhost:8123
- **Kafka UI**: порт 9092 (используйте kafka-tools)

### 5. Первоначальная настройка

```bash
# Инициализация схемы ClickHouse
docker exec -it bionicpro_clickhouse_1 clickhouse-client --query="$(cat sql/clickhouse-init.sql)"

# Проверка DAG в Airflow
# Перейдите в Airflow UI и убедитесь, что все DAG загружены без ошибок
```

## DAG Описание

### 1. bionicpro_etl_master_dag.py
**Расписание**: Каждые 15 минут
**Описание**: Главный оркестратор всех ETL процессов
- Проверка здоровья системы
- Запуск дочерних DAG в правильной последовательности
- Мониторинг выполнения

### 2. crm_integration_dag.py
**Триггер**: Из master DAG
**Описание**: Интеграция с Битрикс24 CRM
- Извлечение данных клиентов
- Извлечение заказов и сделок
- Инкрементальная загрузка в ClickHouse

### 3. telemetry_processing_dag.py
**Триггер**: Из master DAG
**Описание**: Обработка телеметрии ESP32
- Чтение потоковых данных из Kafka
- Валидация и очистка данных
- Создание сессий использования
- Загрузка в ClickHouse

### 4. reports_mart_dag.py
**Триггер**: После telemetry и CRM DAG
**Описание**: Создание витрины отчетов
- Агрегация данных по пользователям
- Расчет KPI и метрик
- Кеширование в Redis

### 5. compliance_audit_dag.py
**Расписание**: Ежедневно в 02:00
**Описание**: GDPR/152-ФЗ соответствие
- Аудит ETL операций
- Шифрование чувствительных данных
- Обработка запросов на удаление данных

## Конфигурация

### Переменные окружения

```bash
# Подключения к внешним системам
export AIRFLOW_CONN_CLICKHOUSE_DEFAULT="clickhouse://default:@clickhouse:8123/default"
export AIRFLOW_CONN_KAFKA_DEFAULT="kafka://kafka:9092"
export AIRFLOW_CONN_BITRIX24_API="https://your-domain.bitrix24.ru/rest/1/token/"

# Шифрование данных
export BIONICPRO_ENCRYPTION_KEY="your-encryption-key-here"

# Размеры батчей для обработки
export AIRFLOW_VAR_BATCH_SIZE_CRM=5000
export AIRFLOW_VAR_BATCH_SIZE_TELEMETRY=10000
```

### Подключения в Airflow

Настройте следующие подключения в Airflow Admin > Connections:

1. **clickhouse_default**
   - Conn Type: Generic
   - Host: clickhouse
   - Port: 8123
   - Schema: bionicpro

2. **kafka_default**
   - Conn Type: Generic
   - Host: kafka
   - Port: 9092

3. **bitrix24_api**
   - Conn Type: HTTP
   - Host: your-domain.bitrix24.ru
   - Extra: {"token": "your-api-token"}

4. **keycloak_db**
   - Conn Type: Postgres
   - Host: postgres-keycloak
   - Port: 5432
   - Schema: keycloak
   - Login: keycloak
   - Password: keycloak

## Безопасность

### Row-Level Security (RLS)

Система использует RLS в ClickHouse для изоляции данных пользователей:

```sql
-- Создание пользователя для API отчетов
CREATE USER reports_user IDENTIFIED WITH sha256_password BY 'secure_password';

-- Политики RLS
CREATE ROW POLICY user_isolation ON telemetry.raw_data
FOR SELECT TO reports_user
USING user_id = currentUser();
```

### Шифрование данных

Чувствительные данные (email, телефоны) автоматически шифруются:

- Алгоритм: AES-256-GCM
- Ключи: Управляются через переменные окружения
- Ротация: Ручная (планируется автоматизация)

### GDPR/152-ФЗ соответствие

- **Право на забвение**: Автоматическое удаление данных по запросу
- **Экспорт данных**: JSON экспорт всех данных пользователя
- **Аудит**: Логирование всех операций с персональными данными
- **Retention**: TTL политики для автоматического удаления старых данных

## Мониторинг

### Метрики Airflow

Система экспортирует метрики в Prometheus:

- `airflow_etl_duration_seconds` - длительность ETL задач
- `airflow_etl_records_processed_total` - количество обработанных записей
- `airflow_data_quality_score` - оценка качества данных

### Алерты

Настроенные алерты в Grafana:

- Сбои ETL процессов (критический)
- Нарушение SLA (критический)
- Деградация качества данных (предупреждение)
- Проблемы с GDPR compliance (критический)

## API интеграция

### Reports API

ETL система подготавливает данные для Reports API:

```bash
# Проверка кеша отчетов
redis-cli GET "user_report:user123:device456"

# Запрос отчета через API
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:3000/api/reports/user123
```

### GraphQL интеграция

```graphql
query GetUserReport($userId: String!, $startDate: Date!, $endDate: Date!) {
  userReport(userId: $userId, startDate: $startDate, endDate: $endDate) {
    dailyUsageHours
    movementEfficiency
    maintenanceScore
    batteryHealth
    anomalyCount
  }
}
```

## Устранение неполадок

### Частые проблемы

1. **DAG не отображается в UI**
   ```bash
   # Проверка ошибок импорта
   docker exec airflow-webserver airflow dags list-import-errors
   ```

2. **Ошибки подключения к ClickHouse**
   ```bash
   # Проверка подключения
   docker exec clickhouse clickhouse-client --query="SELECT 1"
   ```

3. **Проблемы с Kafka**
   ```bash
   # Проверка топиков
   docker exec kafka kafka-topics --list --bootstrap-server kafka:9092
   ```

## Контакты

- **Команда разработки**: dev-team@bionicpro.com
- **Администраторы**: admin@bionicpro.com
- **Безопасность**: security@bionicpro.com
- **Compliance**: compliance@bionicpro.com

## Реализованные требования

✅ **ETL-процесс с использованием Airflow** - реализован с полной оркестрацией
✅ **Извлечение данных из CRM-системы** - интеграция с Битрикс24 через REST API
✅ **Запись в базу OLAP** - ClickHouse как основное хранилище данных
✅ **Витрина данных** - объединение телеметрии и CRM данных
✅ **Быстрый доступ по пользователям** - партиционирование и индексы
✅ **Расписание каждые 15 минут** - соответствует требованиям задачи
✅ **Row-Level Security** - обеспечение изоляции данных пользователей
✅ **GDPR/152-ФЗ соответствие** - полный цикл compliance процессов

Система готова к продуктивному использованию.