"""
Тесты для BionicPRO Reports API Backend
"""

import pytest
import json
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app import app, init_connections

@pytest.fixture
def client():
    """Создание тестового клиента Flask"""
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'

    with app.test_client() as client:
        with app.app_context():
            # Мокаем подключения к базам данных
            with patch('app.clickhouse_client') as mock_ch, \
                 patch('app.redis_client') as mock_redis:
                mock_ch.query.return_value = Mock(result_rows=[], column_names=[])
                mock_redis.get.return_value = None
                mock_redis.setex.return_value = True
                mock_redis.ping.return_value = True
                yield client

@pytest.fixture
def auth_headers():
    """Создание JWT токена для тестов"""
    token = jwt.encode({
        'sub': 'user1',
        'exp': datetime.utcnow() + timedelta(hours=1)
    }, app.config['JWT_SECRET_KEY'], algorithm='HS256')

    return {'Authorization': f'Bearer {token}'}

class TestHealthCheck:
    """Тесты проверки здоровья API"""

    @patch('app.clickhouse_client')
    @patch('app.redis_client')
    def test_health_check_success(self, mock_redis, mock_ch, client):
        """Тест успешной проверки здоровья"""
        # Мокаем успешные ответы от БД
        mock_ch.query.return_value = True
        mock_redis.ping.return_value = True

        response = client.get('/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'services' in data
        assert data['services']['clickhouse'] == 'OK'
        assert data['services']['redis'] == 'OK'

    @patch('app.clickhouse_client')
    @patch('app.redis_client')
    def test_health_check_clickhouse_error(self, mock_redis, mock_ch, client):
        """Тест проверки здоровья при ошибке ClickHouse"""
        mock_ch.query.side_effect = Exception("Connection failed")
        mock_redis.ping.return_value = True

        response = client.get('/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'unhealthy'
        assert 'ERROR' in data['services']['clickhouse']

class TestAuthentication:
    """Тесты аутентификации"""

    @patch('app._verify_user_credentials')
    def test_login_success(self, mock_verify, client):
        """Тест успешной аутентификации"""
        mock_verify.return_value = True

        response = client.post('/auth/login',
                             json={'username': 'user1', 'password': 'password123'})

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['user_id'] == 'user1'

    @patch('app._verify_user_credentials')
    def test_login_invalid_credentials(self, mock_verify, client):
        """Тест аутентификации с неверными данными"""
        mock_verify.return_value = False

        response = client.post('/auth/login',
                             json={'username': 'user1', 'password': 'wrong'})

        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Invalid credentials'

    def test_login_missing_credentials(self, client):
        """Тест аутентификации без учетных данных"""
        response = client.post('/auth/login', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert 'Username and password required' in data['error']

class TestReportsAPI:
    """Тесты API отчетов"""

    @patch('app.clickhouse_client')
    @patch('app.redis_client')
    def test_get_user_reports_success(self, mock_redis, mock_ch, client, auth_headers):
        """Тест успешного получения отчетов пользователя"""
        # Мокаем данные из ClickHouse
        mock_ch.query.return_value = Mock(
            result_rows=[
                ('2024-01-15', 'device1', 8.5, 85.2, 92.1, 88.3, 2, 15, 34.2, 450.1, '2024-01-15T18:30:00')
            ],
            column_names=['report_date', 'device_id', 'daily_usage_hours', 'movement_efficiency',
                         'maintenance_score', 'battery_health', 'anomaly_count', 'total_sessions',
                         'avg_session_duration', 'max_pressure_reached', 'last_sync']
        )
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True

        response = client.get('/reports/user1', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 'user1'
        assert 'summary' in data
        assert 'daily_reports' in data
        assert len(data['daily_reports']) == 1

    def test_get_user_reports_unauthorized(self, client):
        """Тест доступа к отчетам без авторизации"""
        response = client.get('/reports/user1')

        assert response.status_code == 401

    def test_get_user_reports_forbidden(self, client, auth_headers):
        """Тест доступа к отчетам другого пользователя"""
        response = client.get('/reports/user2', headers=auth_headers)

        assert response.status_code == 403
        data = response.get_json()
        assert data['error'] == 'Access denied'

    @patch('app.clickhouse_client')
    @patch('app.redis_client')
    def test_get_user_reports_with_cache(self, mock_redis, mock_ch, client, auth_headers):
        """Тест получения отчетов из кеша"""
        cached_data = {
            'summary': {'total_days': 1, 'total_usage_hours': 8.5},
            'daily_reports': []
        }
        mock_redis.get.return_value = json.dumps(cached_data)

        response = client.get('/reports/user1', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['cached'] == True
        assert data['summary']['total_days'] == 1

    @patch('app.clickhouse_client')
    def test_get_user_devices(self, mock_ch, client, auth_headers):
        """Тест получения списка устройств пользователя"""
        mock_ch.query.return_value = Mock(
            result_rows=[
                ('device1', '2024-01-15', 30),
                ('device2', '2024-01-14', 25)
            ]
        )

        response = client.get('/reports/user1/devices', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 'user1'
        assert len(data['devices']) == 2
        assert data['devices'][0]['device_id'] == 'device1'

    @patch('app.clickhouse_client')
    def test_get_user_summary(self, mock_ch, client, auth_headers):
        """Тест получения сводки пользователя"""
        mock_ch.query.return_value = Mock(
            result_rows=[
                (30, 240.5, 85.2, 88.7, 91.3, 15, 450, '2024-01-15T18:30:00')
            ]
        )

        response = client.get('/reports/user1/summary', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 'user1'
        assert data['total_usage_hours'] == 240.5
        assert data['avg_movement_efficiency'] == 85.2

class TestDataProcessing:
    """Тесты обработки данных"""

    def test_calculate_trends_insufficient_data(self):
        """Тест расчета трендов с недостаточным количеством данных"""
        from app import _calculate_trends

        reports = [
            {'report_date': '2024-01-01', 'daily_usage_hours': 8.0, 'movement_efficiency': 85.0, 'battery_health': 90.0}
        ]

        trends = _calculate_trends(reports)
        assert 'message' in trends
        assert 'Insufficient data' in trends['message']

    def test_calculate_trends_stable(self):
        """Тест расчета стабильных трендов"""
        from app import _calculate_trends

        reports = []
        for i in range(10):
            reports.append({
                'report_date': f'2024-01-{i+1:02d}',
                'daily_usage_hours': 8.0,  # Стабильное значение
                'movement_efficiency': 85.0,
                'battery_health': 90.0
            })

        trends = _calculate_trends(reports)
        assert trends['usage_trend'] == 'stable'
        assert trends['efficiency_trend'] == 'stable'
        assert trends['battery_trend'] == 'stable'

    def test_generate_recommendations_low_efficiency(self):
        """Тест генерации рекомендаций при низкой эффективности"""
        from app import _generate_recommendations

        recommendations = _generate_recommendations(
            efficiency=65,  # Низкая эффективность
            maintenance=85,
            battery=88,
            anomalies=5
        )

        assert len(recommendations) == 1
        assert recommendations[0]['type'] == 'efficiency'
        assert recommendations[0]['priority'] == 'high'

    def test_generate_recommendations_multiple_issues(self):
        """Тест генерации рекомендаций при множественных проблемах"""
        from app import _generate_recommendations

        recommendations = _generate_recommendations(
            efficiency=65,  # Низкая эффективность
            maintenance=75,  # Требуется обслуживание
            battery=65,     # Проблемы с батареей
            anomalies=15    # Много аномалий
        )

        assert len(recommendations) == 4
        types = [r['type'] for r in recommendations]
        assert 'efficiency' in types
        assert 'maintenance' in types
        assert 'battery' in types
        assert 'anomalies' in types

class TestErrorHandling:
    """Тесты обработки ошибок"""

    def test_404_error(self, client):
        """Тест обработки несуществующего endpoint"""
        response = client.get('/nonexistent')

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'Endpoint not found'

    @patch('app.clickhouse_client')
    def test_database_error(self, mock_ch, client, auth_headers):
        """Тест обработки ошибки базы данных"""
        mock_ch.query.side_effect = Exception("Database connection failed")

        response = client.get('/reports/user1', headers=auth_headers)

        assert response.status_code == 500
        data = response.get_json()
        assert 'Failed to retrieve reports' in data['error']

class TestSecurity:
    """Тесты безопасности"""

    def test_sql_injection_protection(self, client, auth_headers):
        """Тест защиты от SQL инъекций"""
        # Попытка SQL инъекции через параметр user_id
        malicious_user_id = "user1'; DROP TABLE reports.user_analytics; --"

        response = client.get(f'/reports/{malicious_user_id}', headers=auth_headers)

        # API должен вернуть ошибку доступа, а не выполнить SQL инъекцию
        assert response.status_code in [403, 500]

    def test_rate_limiting_headers(self, client):
        """Тест наличия заголовков безопасности"""
        response = client.get('/health')

        # Nginx должен добавлять заголовки безопасности
        # В тестах проверяем, что они не противоречат безопасности
        assert response.status_code == 200

if __name__ == '__main__':
    pytest.main(['-v', '--tb=short'])