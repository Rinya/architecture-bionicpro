-- ClickHouse initialization script for BionicPRO ETL
-- Создание базы данных и схем

CREATE DATABASE IF NOT EXISTS bionicpro;

-- Создание схем для разделения данных
CREATE DATABASE IF NOT EXISTS crm;
CREATE DATABASE IF NOT EXISTS telemetry;
CREATE DATABASE IF NOT EXISTS reports;
CREATE DATABASE IF NOT EXISTS audit;

-- =====================================================
-- CRM СХЕМА - данные из Битрикс24
-- =====================================================

-- Таблица клиентов
CREATE TABLE IF NOT EXISTS crm.customers (
    customer_id String,
    user_id String,
    first_name String,
    last_name String,
    email String,
    phone String,
    region String,
    registration_date DateTime,
    status String,
    bitrix_contact_id String,
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(registration_date)
ORDER BY (user_id, customer_id)
SETTINGS index_granularity = 8192;

-- Таблица заказов
CREATE TABLE IF NOT EXISTS crm.orders (
    order_id String,
    customer_id String,
    user_id String,
    prosthetic_type String,
    order_date DateTime,
    delivery_date Nullable(DateTime),
    status String,
    price Decimal(10,2),
    bitrix_deal_id String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(order_date)
ORDER BY (user_id, order_id)
SETTINGS index_granularity = 8192;

-- Таблица протезов
CREATE TABLE IF NOT EXISTS crm.prosthetics (
    prosthetic_id String,
    customer_id String,
    user_id String,
    device_serial String,
    model String,
    firmware_version String,
    activation_date DateTime,
    warranty_expiry DateTime,
    status String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(activation_date)
ORDER BY (user_id, prosthetic_id)
SETTINGS index_granularity = 8192;

-- =====================================================
-- TELEMETRY СХЕМА - данные от ESP32 протезов
-- =====================================================

-- Сырые данные телеметрии
CREATE TABLE IF NOT EXISTS telemetry.raw_data (
    device_id String,
    user_id String,
    timestamp DateTime,
    sensor_type String,
    sensor_value Float64,
    battery_level Float32,
    signal_strength Int8,
    firmware_version String,
    location_lat Nullable(Float64),
    location_lon Nullable(Float64),
    metadata String,
    received_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY (toYYYYMM(timestamp), cityHash64(user_id) % 10)
ORDER BY (user_id, device_id, timestamp)
SETTINGS index_granularity = 8192;

-- Добавление индексов
ALTER TABLE telemetry.raw_data ADD INDEX idx_user_device (user_id, device_id) TYPE bloom_filter GRANULARITY 1;
ALTER TABLE telemetry.raw_data ADD INDEX idx_timestamp timestamp TYPE minmax GRANULARITY 1;

-- Обработанная телеметрия
CREATE TABLE IF NOT EXISTS telemetry.processed_data (
    device_id String,
    user_id String,
    session_id String,
    start_time DateTime,
    end_time DateTime,
    duration_minutes Float32,
    movement_count Int32,
    avg_pressure Float32,
    max_pressure Float32,
    battery_consumed Float32,
    anomalies Array(String),
    quality_score Float32,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY (toYYYYMM(start_time), cityHash64(user_id) % 10)
ORDER BY (user_id, device_id, start_time)
SETTINGS index_granularity = 8192;

-- =====================================================
-- REPORTS СХЕМА - витрина данных для отчетов
-- =====================================================

-- Основная витрина
CREATE TABLE IF NOT EXISTS reports.user_analytics (
    user_id String,
    device_id String,
    report_date Date,
    daily_usage_hours Float32,
    movement_efficiency Float32,
    maintenance_score Float32,
    battery_health Float32,
    anomaly_count Int32,
    total_sessions Int32,
    avg_session_duration Float32,
    max_pressure_reached Float32,
    last_sync DateTime,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, report_date, device_id)
SETTINGS index_granularity = 8192;

ALTER TABLE reports.user_analytics ADD INDEX idx_user_date (user_id, report_date) TYPE minmax GRANULARITY 1;

-- Агрегированная статистика по часам
CREATE TABLE IF NOT EXISTS reports.hourly_stats (
    device_id String,
    user_id String,
    hour DateTime,
    measurement_count UInt64,
    avg_battery_level Float32,
    avg_signal_strength Float32,
    sensor_value_sum Float64,
    created_at DateTime DEFAULT now()
) ENGINE = SummingMergeTree((measurement_count, sensor_value_sum))
PARTITION BY toYYYYMMDD(hour)
ORDER BY (device_id, user_id, hour)
SETTINGS index_granularity = 1024;

-- Materialized View — работает с DateTime, без изменений
CREATE MATERIALIZED VIEW reports.hourly_stats_mv TO reports.hourly_stats
AS SELECT
    device_id,
    user_id,
    toStartOfHour(timestamp) as hour,
    count() as measurement_count,
    avg(battery_level) as avg_battery_level,
    avg(signal_strength) as avg_signal_strength,
    sum(sensor_value) as sensor_value_sum,
    now() as created_at
FROM telemetry.raw_data
GROUP BY device_id, user_id, hour;

-- =====================================================
-- AUDIT СХЕМА - аудит и compliance
-- =====================================================

-- Таблица аудита ETL
CREATE TABLE IF NOT EXISTS audit.etl_operations (
    operation_id String,
    dag_id String,
    task_id String,
    user_id Nullable(String),
    operation_type String,
    table_name String,
    records_processed Int64,
    start_time DateTime,
    end_time Nullable(DateTime),
    status String,
    error_message Nullable(String),
    data_checksum String,
    compliance_flags Array(String),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_time)
ORDER BY (start_time, dag_id, task_id)
SETTINGS index_granularity = 8192;

-- Таблица GDPR запросов
CREATE TABLE IF NOT EXISTS audit.gdpr_requests (
    request_id String,
    user_id String,
    request_type String,
    request_date DateTime,
    processed_date Nullable(DateTime),
    status String,
    affected_tables Array(String),
    deletion_reason String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(request_date)
ORDER BY (request_date, user_id)
SETTINGS index_granularity = 8192;

-- =====================================================
-- ФУНКЦИИ ДЛЯ БИЗНЕС-ЛОГИКИ
-- =====================================================

CREATE FUNCTION calculateMaintenanceScore AS (avg_pressure, max_pressure) ->
    if(max_pressure = 0, 0,
       round(100 - (abs(avg_pressure - max_pressure) / max_pressure * 100), 2));

CREATE FUNCTION validateUserAccess AS (requested_user_id) ->
    if(requested_user_id = currentUser() OR hasRole('admin'), 1, 0);


-- =====================================================
-- ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- =====================================================

-- Компрессия
ALTER TABLE telemetry.raw_data MODIFY COLUMN metadata Codec(ZSTD(1));
ALTER TABLE audit.etl_operations MODIFY COLUMN error_message Codec(LZ4HC(9));

-- TTL — теперь работает, так как timestamp имеет тип DateTime
ALTER TABLE telemetry.raw_data MODIFY TTL timestamp + INTERVAL 3 YEAR;
ALTER TABLE audit.etl_operations MODIFY TTL start_time + INTERVAL 7 YEAR;

-- =====================================================
-- INITIAL DATA SETUP
-- =====================================================
--INSERT INTO telemetry.raw_data VALUES
--('esp32-001', 'user1', now(), 'pressure', 75.5, 85.2, -70, '1.2.3', NULL, NULL, '{"temperature": 36.6}', now());

-- Сообщение об успешной инициализации
SELECT 'ClickHouse schema for BionicPRO ETL initialized successfully!' as status;