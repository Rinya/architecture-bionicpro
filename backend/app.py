"""
BionicPRO Reports API Backend
Flask приложение для предоставления отчетов пользователям о работе их протезов
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from werkzeug.security import check_password_hash
import clickhouse_connect
import redis
import json
import logging
from datetime import datetime, timedelta
import os
from functools import wraps
import hashlib

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание Flask приложения
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'bionicpro-secret-key-2024')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Инициализация расширений
jwt = JWTManager(app)
CORS(app, origins=['http://localhost:3000'])  # React frontend

# Подключения к базам данных
CLICKHOUSE_CONFIG = {
    'host': os.environ.get('CLICKHOUSE_HOST', 'localhost'),
    'port': int(os.environ.get('CLICKHOUSE_PORT', 8123)),
    'database': os.environ.get('CLICKHOUSE_DB', 'bionicpro'),
    'username': os.environ.get('CLICKHOUSE_USER', 'reports_user'),
    'password': os.environ.get('CLICKHOUSE_PASSWORD', 'secure_reports_password_2024!')
}

REDIS_CONFIG = {
    'host': os.environ.get('REDIS_HOST', 'localhost'),
    'port': int(os.environ.get('REDIS_PORT', 6379)),
    'db': 0,
    'decode_responses': True
}

# Глобальные подключения
clickhouse_client = None
redis_client = None

def init_connections():
    """Инициализация подключений к базам данных"""
    global clickhouse_client, redis_client

    try:
        # Подключение к ClickHouse
        clickhouse_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
        logger.info("✅ Connected to ClickHouse")

        # Подключение к Redis
        redis_client = redis.Redis(**REDIS_CONFIG)
        redis_client.ping()
        logger.info("✅ Connected to Redis")

    except Exception as e:
        logger.error(f"❌ Failed to initialize connections: {e}")
        raise

def require_user_access(f):
    """Декоратор для проверки доступа пользователя к своим данным"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            current_user = get_jwt_identity()
            requested_user = request.view_args.get('user_id') or request.json.get('user_id')

            # Проверка доступа: пользователь может видеть только свои данные
            if current_user != requested_user and not _is_admin(current_user):
                return jsonify({
                    'error': 'Access denied',
                    'message': 'You can only access your own reports'
                }), 403

            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Access control error: {e}")
            return jsonify({'error': 'Access control failed'}), 500

    return decorated_function

def _is_admin(user_id):
    """Проверка является ли пользователь администратором"""
    # В реальной системе это будет запрос к базе ролей
    admin_users = os.environ.get('ADMIN_USERS', '').split(',')
    return user_id in admin_users

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка состояния API"""
    try:
        # Проверка ClickHouse
        clickhouse_client.query("SELECT 1")
        clickhouse_status = "OK"
    except Exception as e:
        clickhouse_status = f"ERROR: {str(e)}"

    try:
        # Проверка Redis
        redis_client.ping()
        redis_status = "OK"
    except Exception as e:
        redis_status = f"ERROR: {str(e)}"

    return jsonify({
        'status': 'healthy' if clickhouse_status == "OK" and redis_status == "OK" else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'clickhouse': clickhouse_status,
            'redis': redis_status
        }
    })

@app.route('/auth/login', methods=['POST'])
def login():
    """Аутентификация пользователя и выдача JWT токена"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        # В реальной системе проверка будет через Keycloak
        # Здесь упрощенная проверка для демонстрации
        if _verify_user_credentials(username, password):
            access_token = create_access_token(identity=username)

            return jsonify({
                'access_token': access_token,
                'user_id': username,
                'expires_in': app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()
            })
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

def _verify_user_credentials(username, password):
    """Упрощенная проверка учетных данных"""
    # В реальной системе это будет интеграция с Keycloak
    # Для демонстрации используем простую проверку
    test_users = {
        'user1': 'password123',
        'user2': 'password456',
        'admin': 'admin123'
    }
    return test_users.get(username) == password

@app.route('/reports/<user_id>', methods=['GET'])
@jwt_required()
@require_user_access
def get_user_reports(user_id):
    """
    Получение отчетов пользователя за указанный период

    Query параметры:
    - start_date: начальная дата (YYYY-MM-DD)
    - end_date: конечная дата (YYYY-MM-DD)
    - device_id: конкретное устройство (опционально)
    - format: json|pdf|excel (по умолчанию json)
    """
    try:
        # Получение параметров запроса
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).date().isoformat())
        end_date = request.args.get('end_date', datetime.now().date().isoformat())
        device_id = request.args.get('device_id')
        format_type = request.args.get('format', 'json')

        logger.info(f"📊 Getting reports for user {user_id}, period: {start_date} to {end_date}")

        # Проверка кеша Redis
        cache_key = f"user_report:{user_id}:{start_date}:{end_date}:{device_id or 'all'}"
        cached_report = redis_client.get(cache_key)

        if cached_report and format_type == 'json':
            logger.info(f"🚀 Serving cached report for user {user_id}")
            return jsonify({
                'user_id': user_id,
                'cached': True,
                **json.loads(cached_report)
            })

        # Проверка доступности данных (обработаны ли Airflow)
        data_availability = _check_data_availability(start_date, end_date)
        if not data_availability['data_available']:
            return jsonify({
                'error': 'Data not available',
                'message': data_availability['message'],
                'available_until': data_availability['available_until'],
                'requested_period': {'start_date': start_date, 'end_date': end_date}
            }), 400

        # Построение SQL запроса с Row-Level Security
        query = _build_reports_query(user_id, start_date, end_date, device_id)

        # Выполнение запроса к ClickHouse
        logger.info(f"🔍 Executing query for user {user_id}")
        result = clickhouse_client.query(query)

        # Обработка результатов
        reports_data = _process_reports_data(result.result_rows, result.column_names)

        # Кеширование результата на 1 час
        if reports_data['summary']['total_days'] > 0:
            redis_client.setex(
                cache_key,
                3600,  # 1 час TTL
                json.dumps(reports_data)
            )

        # Логирование доступа для аудита
        _log_report_access(user_id, start_date, end_date, len(reports_data['daily_reports']))

        # Возврат данных в зависимости от формата
        if format_type == 'json':
            return jsonify({
                'user_id': user_id,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'cached': False,
                **reports_data
            })
        elif format_type == 'pdf':
            return _generate_pdf_report(user_id, reports_data)
        elif format_type == 'excel':
            return _generate_excel_report(user_id, reports_data)
        else:
            return jsonify({'error': 'Unsupported format'}), 400

    except Exception as e:
        logger.error(f"❌ Error getting reports for user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to retrieve reports',
            'message': str(e)
        }), 500

def _check_data_availability(start_date, end_date):
    """
    Проверка что запрашиваемые данные уже обработаны Airflow ETL

    Возвращает информацию о доступности данных для указанного периода
    """
    try:
        from datetime import datetime, timedelta

        # Конвертируем даты
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Airflow ETL обрабатывает данные с задержкой
        # Данные за вчера должны быть доступны, за сегодня - возможно нет
        yesterday = (datetime.now() - timedelta(days=1)).date()
        two_days_ago = (datetime.now() - timedelta(days=2)).date()

        # Проверяем, не запрашивает ли пользователь будущие данные
        today = datetime.now().date()
        if end_dt > today:
            return {
                'data_available': False,
                'message': 'Данные за будущие даты недоступны',
                'available_until': today.isoformat(),
                'reason': 'future_dates'
            }

        # Проверяем свежесть последней ETL обработки из ClickHouse
        try:
            # Проверяем когда в последний раз обновлялись данные в reports.user_analytics
            freshness_query = """
            SELECT
                max(created_at) as last_etl_run,
                max(report_date) as latest_report_date,
                count(*) as total_records
            FROM reports.user_analytics
            WHERE created_at >= today() - INTERVAL 3 DAY
            """

            result = clickhouse_client.query(freshness_query)

            if result.result_rows:
                last_etl_run, latest_report_date, total_records = result.result_rows[0]

                # Если нет недавних обновлений данных
                if not last_etl_run:
                    return {
                        'data_available': False,
                        'message': 'ETL система не выполняла обновления в последние 3 дня',
                        'available_until': two_days_ago.isoformat(),
                        'reason': 'etl_not_running'
                    }

                # Проверяем возраст последних данных
                etl_age_hours = (datetime.now() - last_etl_run).total_seconds() / 3600

                # Если ETL не запускался больше 2 часов, данные могут быть неполными
                if etl_age_hours > 2:
                    # Ограничиваем доступные данные до позавчера
                    if end_dt > two_days_ago:
                        return {
                            'data_available': False,
                            'message': f'Данные не обновлялись {etl_age_hours:.1f} часов. Доступны данные до {two_days_ago}',
                            'available_until': two_days_ago.isoformat(),
                            'reason': 'stale_data'
                        }

                # Если ETL свежий, данные до вчера должны быть доступны
                if end_dt > yesterday:
                    return {
                        'data_available': False,
                        'message': 'Данные за сегодня ещё обрабатываются ETL системой',
                        'available_until': yesterday.isoformat(),
                        'reason': 'processing_delay'
                    }

                return {
                    'data_available': True,
                    'message': 'Данные доступны',
                    'available_until': yesterday.isoformat(),
                    'last_etl_run': last_etl_run.isoformat() if last_etl_run else None
                }
            else:
                return {
                    'data_available': False,
                    'message': 'Нет данных в системе отчётов',
                    'available_until': None,
                    'reason': 'no_data'
                }

        except Exception as e:
            logger.warning(f"Error checking data freshness: {e}")
            # В случае ошибки проверки, ограничиваем до позавчера для безопасности
            return {
                'data_available': end_dt <= two_days_ago,
                'message': f'Ошибка проверки свежести данных. Доступны данные до {two_days_ago}',
                'available_until': two_days_ago.isoformat(),
                'reason': 'check_error'
            }

    except Exception as e:
        logger.error(f"Data availability check failed: {e}")
        return {
            'data_available': False,
            'message': 'Ошибка проверки доступности данных',
            'available_until': None,
            'reason': 'system_error'
        }

def _build_reports_query(user_id, start_date, end_date, device_id=None):
    """Построение SQL запроса с учетом Row-Level Security"""

    device_filter = f"AND device_id = '{device_id}'" if device_id else ""

    # Основной запрос к витрине отчетов
    query = f"""
    SELECT
        report_date,
        device_id,
        daily_usage_hours,
        movement_efficiency,
        maintenance_score,
        battery_health,
        anomaly_count,
        total_sessions,
        avg_session_duration,
        max_pressure_reached,
        last_sync
    FROM reports.user_analytics
    WHERE user_id = '{user_id}'
      AND report_date >= '{start_date}'
      AND report_date <= '{end_date}'
      {device_filter}
    ORDER BY report_date DESC, device_id
    """

    return query

def _process_reports_data(rows, columns):
    """Обработка данных отчета и расчет агрегированных метрик"""

    # Создание DataFrame-подобной структуры
    reports = []
    for row in rows:
        report = dict(zip(columns, row))

        # Конвертация типов и форматирование
        report['report_date'] = report['report_date'].isoformat() if report['report_date'] else None
        report['daily_usage_hours'] = round(float(report['daily_usage_hours'] or 0), 2)
        report['movement_efficiency'] = round(float(report['movement_efficiency'] or 0), 1)
        report['maintenance_score'] = round(float(report['maintenance_score'] or 0), 1)
        report['battery_health'] = round(float(report['battery_health'] or 0), 1)
        report['anomaly_count'] = int(report['anomaly_count'] or 0)
        report['total_sessions'] = int(report['total_sessions'] or 0)
        report['avg_session_duration'] = round(float(report['avg_session_duration'] or 0), 2)
        report['max_pressure_reached'] = round(float(report['max_pressure_reached'] or 0), 1)
        report['last_sync'] = report['last_sync'].isoformat() if report['last_sync'] else None

        reports.append(report)

    # Расчет агрегированных метрик
    if reports:
        total_usage = sum(r['daily_usage_hours'] for r in reports)
        avg_efficiency = sum(r['movement_efficiency'] for r in reports) / len(reports)
        avg_maintenance = sum(r['maintenance_score'] for r in reports) / len(reports)
        avg_battery = sum(r['battery_health'] for r in reports) / len(reports)
        total_anomalies = sum(r['anomaly_count'] for r in reports)
        total_sessions = sum(r['total_sessions'] for r in reports)

        # Выявление трендов
        trends = _calculate_trends(reports)

        # Рекомендации
        recommendations = _generate_recommendations(avg_efficiency, avg_maintenance, avg_battery, total_anomalies)

    else:
        total_usage = avg_efficiency = avg_maintenance = avg_battery = 0
        total_anomalies = total_sessions = 0
        trends = {}
        recommendations = []

    return {
        'summary': {
            'total_days': len(reports),
            'total_usage_hours': round(total_usage, 2),
            'avg_movement_efficiency': round(avg_efficiency, 1),
            'avg_maintenance_score': round(avg_maintenance, 1),
            'avg_battery_health': round(avg_battery, 1),
            'total_anomalies': total_anomalies,
            'total_sessions': total_sessions
        },
        'trends': trends,
        'recommendations': recommendations,
        'daily_reports': reports
    }

def _calculate_trends(reports):
    """Расчет трендов показателей"""
    if len(reports) < 7:
        return {'message': 'Insufficient data for trend analysis'}

    # Сортируем по дате
    sorted_reports = sorted(reports, key=lambda x: x['report_date'])

    # Разделяем на первую и вторую половину периода
    mid_point = len(sorted_reports) // 2
    first_half = sorted_reports[:mid_point]
    second_half = sorted_reports[mid_point:]

    # Расчет средних значений
    first_avg_usage = sum(r['daily_usage_hours'] for r in first_half) / len(first_half)
    second_avg_usage = sum(r['daily_usage_hours'] for r in second_half) / len(second_half)

    first_avg_efficiency = sum(r['movement_efficiency'] for r in first_half) / len(first_half)
    second_avg_efficiency = sum(r['movement_efficiency'] for r in second_half) / len(second_half)

    first_avg_battery = sum(r['battery_health'] for r in first_half) / len(first_half)
    second_avg_battery = sum(r['battery_health'] for r in second_half) / len(second_half)

    return {
        'usage_trend': _get_trend_direction(first_avg_usage, second_avg_usage),
        'efficiency_trend': _get_trend_direction(first_avg_efficiency, second_avg_efficiency),
        'battery_trend': _get_trend_direction(first_avg_battery, second_avg_battery)
    }

def _get_trend_direction(first_value, second_value):
    """Определение направления тренда"""
    diff_percent = ((second_value - first_value) / first_value * 100) if first_value > 0 else 0

    if diff_percent > 5:
        return 'improving'
    elif diff_percent < -5:
        return 'declining'
    else:
        return 'stable'

def _generate_recommendations(efficiency, maintenance, battery, anomalies):
    """Генерация рекомендаций на основе показателей"""
    recommendations = []

    if efficiency < 70:
        recommendations.append({
            'type': 'efficiency',
            'priority': 'high',
            'title': 'Низкая эффективность движений',
            'message': 'Рекомендуется пройти дополнительную калибровку протеза',
            'action': 'Schedule calibration session'
        })

    if maintenance < 80:
        recommendations.append({
            'type': 'maintenance',
            'priority': 'medium',
            'title': 'Требуется техническое обслуживание',
            'message': 'Показатели состояния протеза снижены. Обратитесь в сервис',
            'action': 'Contact support service'
        })

    if battery < 70:
        recommendations.append({
            'type': 'battery',
            'priority': 'high',
            'title': 'Проблемы с батареей',
            'message': 'Здоровье батареи критически низкое. Возможно требуется замена',
            'action': 'Replace battery'
        })

    if anomalies > 10:
        recommendations.append({
            'type': 'anomalies',
            'priority': 'high',
            'title': 'Высокое количество аномалий',
            'message': 'Обнаружено много нештатных ситуаций. Проверьте настройки',
            'action': 'Review prosthetic settings'
        })

    return recommendations

def _log_report_access(user_id, start_date, end_date, records_count):
    """Логирование доступа к отчетам для аудита"""
    try:
        audit_record = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': 'REPORT_ACCESS',
            'start_date': start_date,
            'end_date': end_date,
            'records_returned': records_count,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }

        # Сохранение в Redis для последующей обработки ETL
        redis_client.lpush('audit:report_access', json.dumps(audit_record))

        logger.info(f"📝 Logged report access: {user_id} accessed {records_count} records")

    except Exception as e:
        logger.error(f"Failed to log report access: {e}")

def _generate_pdf_report(user_id, reports_data):
    """Генерация PDF отчета (заглушка)"""
    # В реальной системе здесь будет интеграция с библиотекой генерации PDF
    return jsonify({
        'message': 'PDF generation not implemented yet',
        'user_id': user_id,
        'summary': reports_data['summary']
    }), 501

def _generate_excel_report(user_id, reports_data):
    """Генерация Excel отчета (заглушка)"""
    # В реальной системе здесь будет интеграция с библиотекой генерации Excel
    return jsonify({
        'message': 'Excel generation not implemented yet',
        'user_id': user_id,
        'summary': reports_data['summary']
    }), 501

@app.route('/reports/<user_id>/devices', methods=['GET'])
@jwt_required()
@require_user_access
def get_user_devices(user_id):
    """Получение списка устройств пользователя"""
    try:
        query = f"""
        SELECT DISTINCT
            device_id,
            max(report_date) as last_report_date,
            count(*) as total_reports
        FROM reports.user_analytics
        WHERE user_id = '{user_id}'
        GROUP BY device_id
        ORDER BY last_report_date DESC
        """

        result = clickhouse_client.query(query)

        devices = []
        for row in result.result_rows:
            device_id, last_report, total_reports = row
            devices.append({
                'device_id': device_id,
                'last_report_date': last_report.isoformat() if last_report else None,
                'total_reports': int(total_reports)
            })

        return jsonify({
            'user_id': user_id,
            'devices': devices
        })

    except Exception as e:
        logger.error(f"❌ Error getting devices for user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to retrieve devices',
            'message': str(e)
        }), 500

@app.route('/reports/<user_id>/summary', methods=['GET'])
@jwt_required()
@require_user_access
def get_user_summary(user_id):
    """Получение краткой сводки по пользователю"""
    try:
        # Запрос агрегированной статистики за последние 30 дней
        query = f"""
        SELECT
            count(*) as total_days,
            sum(daily_usage_hours) as total_usage_hours,
            avg(movement_efficiency) as avg_efficiency,
            avg(maintenance_score) as avg_maintenance,
            avg(battery_health) as avg_battery_health,
            sum(anomaly_count) as total_anomalies,
            sum(total_sessions) as total_sessions,
            max(last_sync) as last_activity
        FROM reports.user_analytics
        WHERE user_id = '{user_id}'
          AND report_date >= today() - INTERVAL 30 DAY
        """

        result = clickhouse_client.query(query)
        row = result.result_rows[0] if result.result_rows else [0] * 8

        summary = {
            'user_id': user_id,
            'period_days': 30,
            'total_days_with_data': int(row[0]),
            'total_usage_hours': round(float(row[1] or 0), 2),
            'avg_movement_efficiency': round(float(row[2] or 0), 1),
            'avg_maintenance_score': round(float(row[3] or 0), 1),
            'avg_battery_health': round(float(row[4] or 0), 1),
            'total_anomalies': int(row[5] or 0),
            'total_sessions': int(row[6] or 0),
            'last_activity': row[7].isoformat() if row[7] else None
        }

        return jsonify(summary)

    except Exception as e:
        logger.error(f"❌ Error getting summary for user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to retrieve summary',
            'message': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized access'}), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Access forbidden'}), 403

if __name__ == '__main__':
    # Инициализация подключений
    init_connections()

    # Запуск сервера
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'

    logger.info(f"🚀 Starting BionicPRO Reports API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)