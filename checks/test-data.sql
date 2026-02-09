-- Вставка тестовых данных для демонстрации
INSERT INTO user_analytics
(user_id, device_id, report_date, daily_usage_hours, movement_efficiency, maintenance_score, battery_health, anomaly_count, total_sessions, avg_session_duration, max_pressure_reached, last_sync, created_at, updated_at)
VALUES
    ('user1', 'ESP32-001-BP', '2024-01-15', 8.5, 87.2, 92.1, 89.3, 2, 12, 42.5, 850.0, '2024-01-15 23:45:00', now(), now()),
    ('user1', 'ESP32-001-BP', '2024-01-16', 7.2, 85.1, 90.8, 87.1, 1, 10, 43.2, 820.0, '2024-01-16 23:30:00', now(), now()),
    ('user1', 'ESP32-001-BP', '2024-01-17', 6.8, 88.5, 93.2, 91.5, 0, 9, 45.3, 780.0, '2024-01-17 22:15:00', now(), now()),
    ('user2', 'ESP32-002-BP', '2024-01-15', 5.5, 75.2, 85.1, 78.3, 4, 8, 41.0, 920.0, '2024-01-15 23:20:00', now(), now()),
    ('user2', 'ESP32-002-BP', '2024-01-16', 6.2, 77.8, 87.5, 80.1, 2, 10, 37.2, 880.0, '2024-01-16 22:45:00', now(), now());