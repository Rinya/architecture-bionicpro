-- Добавление свежих данных
INSERT INTO user_analytics
(user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at, updated_at)
VALUES
    ('user1', 'ESP32-001-BP', today() - 1, 7.5, 86.2, 91.1, 88.3, 1, 11, 41.5, 860.0, now() - INTERVAL 1 HOUR, now(), now()),
    ('user1', 'ESP32-001-BP', today() - 2, 8.1, 89.1, 93.5, 90.2, 0, 13, 38.2, 790.0, now() - INTERVAL 25 HOUR, now(), now());