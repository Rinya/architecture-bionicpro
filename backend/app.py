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
import requests
import jwt as jwt_lib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import base64
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.chart import LineChart, Reference
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import json
import logging
from datetime import datetime, timedelta
import os
from functools import wraps
import hashlib
import math

# Кастомный JSON encoder для обработки NaN значений
class SafeJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return '0.0'
        return super().encode(obj)

    def iterencode(self, obj, _one_shot=False):
        """Encode the given object and yield each string representation as available."""
        if isinstance(obj, dict):
            obj = {k: (0.0 if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
                   for k, v in obj.items()}
        elif isinstance(obj, list):
            obj = [0.0 if isinstance(item, float) and (math.isnan(item) or math.isinf(item)) else item
                   for item in obj]
        elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            obj = 0.0

        return super().iterencode(obj, _one_shot)

# Функция для рекурсивной очистки данных от NaN
def clean_nan_values(obj):
    """Рекурсивно заменяет NaN и бесконечные значения на 0"""
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    return obj

# Безопасная функция round для обработки NaN
def safe_round(value, decimals=0):
    """Безопасное округление с защитой от NaN"""
    try:
        if isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                return 0.0
            return round(value, decimals)
        return 0.0
    except (ValueError, TypeError):
        return 0.0

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание Flask приложения
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'bionicpro-secret-key-2024')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Применение кастомного JSON encoder для обработки NaN
app.json_encoder = SafeJSONEncoder

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
    'password': os.environ.get('REDIS_PASSWORD'),
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

# Инициализация подключений при загрузке модуля
try:
    init_connections()
except Exception as e:
    logger.warning(f"Failed to initialize connections on startup: {e}")

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

@app.route('/auth/keycloak-exchange', methods=['POST'])
def keycloak_token_exchange():
    """Обмен Keycloak токена на backend токен"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401

        keycloak_token = auth_header[7:]  # Remove 'Bearer ' prefix

        # Для упрощения пока используем простую валидацию
        # В реальной системе здесь будет валидация через публичный ключ Keycloak
        try:
            # Декодируем токен без валидации (только для получения payload)
            decoded = jwt_lib.decode(keycloak_token, options={"verify_signature": False})
            username = decoded.get('preferred_username') or decoded.get('sub')

            if not username:
                return jsonify({'error': 'Invalid token: no username found'}), 401

            # Создаем новый backend токен
            access_token = create_access_token(identity=username)

            return jsonify({
                'access_token': access_token,
                'user_id': username,
                'expires_in': app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()
            })

        except Exception as token_error:
            logger.error(f"Token validation error: {token_error}")
            return jsonify({'error': 'Invalid token'}), 401

    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        return jsonify({'error': 'Token exchange failed'}), 500

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
            cached_data = {
                'user_id': user_id,
                'cached': True,
                **json.loads(cached_report)
            }
            # Очищаем кешированные данные от возможных NaN значений
            cleaned_cached = clean_nan_values(cached_data)
            return jsonify(cleaned_cached)

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

        # Кеширование результата на 1 час (с очисткой от NaN)
        if reports_data['summary']['total_days'] > 0:
            # Очищаем данные перед кешированием
            cleaned_reports_data = clean_nan_values(reports_data)
            redis_client.setex(
                cache_key,
                3600,  # 1 час TTL
                json.dumps(cleaned_reports_data)
            )

        # Логирование доступа для аудита
        _log_report_access(user_id, start_date, end_date, len(reports_data['daily_reports']))

        # Возврат данных в зависимости от формата
        if format_type == 'json':
            response_data = {
                'user_id': user_id,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'cached': False,
                **reports_data
            }
            # Очищаем данные от возможных NaN значений перед отправкой
            cleaned_response = clean_nan_values(response_data)
            return jsonify(cleaned_response)
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

        # Функция для безопасной обработки числовых значений, включая NaN
        def safe_float(value, default=0.0):
            try:
                if value is None:
                    return default
                result = float(value)
                # Проверяем на NaN и бесконечность
                if result != result or result == float('inf') or result == float('-inf'):
                    return default
                return result
            except (ValueError, TypeError):
                return default

        # Конвертация типов и форматирование
        report['report_date'] = report['report_date'].isoformat() if report['report_date'] else None
        report['daily_usage_hours'] = safe_round(safe_float(report['daily_usage_hours']), 2)
        report['movement_efficiency'] = safe_round(safe_float(report['movement_efficiency']), 1)
        report['maintenance_score'] = safe_round(safe_float(report['maintenance_score']), 1)
        report['battery_health'] = safe_round(safe_float(report['battery_health']), 1)
        report['anomaly_count'] = int(report['anomaly_count'] or 0)
        report['total_sessions'] = int(report['total_sessions'] or 0)
        report['avg_session_duration'] = safe_round(safe_float(report['avg_session_duration']), 2)
        report['max_pressure_reached'] = safe_round(safe_float(report['max_pressure_reached']), 1)
        report['last_sync'] = report['last_sync'].isoformat() if report['last_sync'] else None

        reports.append(report)

    # Функция для безопасной обработки числовых значений, включая NaN
    def safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            result = float(value)
            # Проверяем на NaN и бесконечность
            if result != result or result == float('inf') or result == float('-inf'):
                return default
            return result
        except (ValueError, TypeError):
            return default

    # Расчет агрегированных метрик
    if reports:
        total_usage = sum(safe_float(r['daily_usage_hours']) for r in reports)

        # Безопасный расчет средних значений
        efficiency_values = [safe_float(r['movement_efficiency']) for r in reports]
        maintenance_values = [safe_float(r['maintenance_score']) for r in reports]
        battery_values = [safe_float(r['battery_health']) for r in reports]

        avg_efficiency = sum(efficiency_values) / len(reports) if reports else 0
        avg_maintenance = sum(maintenance_values) / len(reports) if reports else 0
        avg_battery = sum(battery_values) / len(reports) if reports else 0

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
            'total_usage_hours': safe_round(total_usage, 2),
            'avg_movement_efficiency': safe_round(avg_efficiency, 1),
            'avg_maintenance_score': safe_round(avg_maintenance, 1),
            'avg_battery_health': safe_round(avg_battery, 1),
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

    # Функция для безопасной обработки числовых значений, включая NaN
    def safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            result = float(value)
            # Проверяем на NaN и бесконечность
            if result != result or result == float('inf') or result == float('-inf'):
                return default
            return result
        except (ValueError, TypeError):
            return default

    # Сортируем по дате
    sorted_reports = sorted(reports, key=lambda x: x['report_date'])

    # Разделяем на первую и вторую половину периода
    mid_point = len(sorted_reports) // 2
    first_half = sorted_reports[:mid_point]
    second_half = sorted_reports[mid_point:]

    # Безопасный расчет средних значений
    first_usage_values = [safe_float(r['daily_usage_hours']) for r in first_half]
    second_usage_values = [safe_float(r['daily_usage_hours']) for r in second_half]

    first_efficiency_values = [safe_float(r['movement_efficiency']) for r in first_half]
    second_efficiency_values = [safe_float(r['movement_efficiency']) for r in second_half]

    first_battery_values = [safe_float(r['battery_health']) for r in first_half]
    second_battery_values = [safe_float(r['battery_health']) for r in second_half]

    first_avg_usage = sum(first_usage_values) / len(first_half) if first_half else 0
    second_avg_usage = sum(second_usage_values) / len(second_half) if second_half else 0

    first_avg_efficiency = sum(first_efficiency_values) / len(first_half) if first_half else 0
    second_avg_efficiency = sum(second_efficiency_values) / len(second_half) if second_half else 0

    first_avg_battery = sum(first_battery_values) / len(first_half) if first_half else 0
    second_avg_battery = sum(second_battery_values) / len(second_half) if second_half else 0

    return {
        'usage_trend': _get_trend_direction(first_avg_usage, second_avg_usage),
        'efficiency_trend': _get_trend_direction(first_avg_efficiency, second_avg_efficiency),
        'battery_trend': _get_trend_direction(first_avg_battery, second_avg_battery)
    }

def _get_trend_direction(first_value, second_value):
    """Определение направления тренда"""
    # Защита от NaN и некорректных значений
    try:
        first_value = float(first_value) if first_value is not None else 0
        second_value = float(second_value) if second_value is not None else 0

        # Проверяем на NaN
        if first_value != first_value or second_value != second_value:
            return 'stable'

        # Защита от деления на ноль
        if first_value <= 0:
            if second_value > 0:
                return 'improving'
            else:
                return 'stable'

        diff_percent = ((second_value - first_value) / first_value * 100)

        # Дополнительная проверка на NaN результата
        if diff_percent != diff_percent:  # NaN check
            return 'stable'

        if diff_percent > 5:
            return 'improving'
        elif diff_percent < -5:
            return 'declining'
        else:
            return 'stable'
    except (ValueError, TypeError, ZeroDivisionError):
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
    """Генерация PDF отчета"""
    try:
        # Создаем буфер в памяти
        buffer = io.BytesIO()

        # Создаем PDF документ
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)

        # Получаем стили
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Центр
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#366092')
        )

        # Элементы документа
        story = []

        # Заголовок
        title = Paragraph(f"Отчет BionicPRO<br/>Пользователь: {user_id}", title_style)
        story.append(title)

        # Период
        period = reports_data.get('period', {})
        period_text = f"Период: {period.get('start_date', '')} - {period.get('end_date', '')}"
        story.append(Paragraph(period_text, styles['Normal']))
        story.append(Spacer(1, 20))

        # Сводка
        story.append(Paragraph("Сводная информация", heading_style))

        summary = reports_data.get('summary', {})
        summary_data = [
            ['Метрика', 'Значение'],
            ['Всего дней с данными', str(summary.get('total_days', 0))],
            ['Общее время использования (часы)', f"{summary.get('total_usage_hours', 0):.1f}"],
            ['Средняя эффективность движения (%)', f"{summary.get('avg_movement_efficiency', 0):.1f}"],
            ['Средняя оценка обслуживания', f"{summary.get('avg_maintenance_score', 0):.1f}"],
            ['Средний уровень батареи (%)', f"{summary.get('avg_battery_health', 0):.1f}"],
            ['Всего аномалий', str(summary.get('total_anomalies', 0))],
            ['Всего сессий', str(summary.get('total_sessions', 0))]
        ]

        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Рекомендации (если есть)
        recommendations = reports_data.get('recommendations', [])
        if recommendations:
            story.append(Paragraph("Рекомендации", heading_style))
            for idx, rec in enumerate(recommendations[:5], 1):  # Максимум 5 рекомендаций
                rec_text = f"{idx}. <b>{rec.get('title', '')}</b><br/>{rec.get('message', '')}"
                story.append(Paragraph(rec_text, styles['Normal']))
                story.append(Spacer(1, 10))

        # Детальные данные (если есть и их не слишком много)
        daily_reports = reports_data.get('daily_reports', [])
        if daily_reports and len(daily_reports) <= 30:  # Максимум 30 строк для PDF
            story.append(Paragraph("Детальные данные (последние записи)", heading_style))

            details_data = [['Дата', 'Устройство', 'Время (ч)', 'Эффективность', 'Батарея']]

            for report in daily_reports[:20]:  # Первые 20 записей
                details_data.append([
                    report.get('report_date', ''),
                    report.get('device_id', '')[:8] + '...' if len(report.get('device_id', '')) > 8 else report.get('device_id', ''),
                    f"{report.get('daily_usage_hours', 0):.1f}",
                    f"{report.get('movement_efficiency', 0):.0f}%",
                    f"{report.get('battery_health', 0):.0f}%"
                ])

            details_table = Table(details_data, colWidths=[1.2*inch, 1.2*inch, 1*inch, 1*inch, 1*inch])
            details_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            story.append(details_table)

        # Создаем PDF
        doc.build(story)
        buffer.seek(0)

        # Возвращаем файл
        from flask import Response

        response = Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=bionicpro_report_{user_id}.pdf'
            }
        )
        return response

    except Exception as e:
        logger.error(f"❌ Error generating PDF report: {e}")
        return jsonify({
            'error': 'Failed to generate PDF report',
            'message': str(e)
        }), 500

def _generate_excel_report(user_id, reports_data):
    """Генерация Excel отчета"""
    try:
        # Создаем новую книгу Excel
        wb = Workbook()

        # Удаляем стандартный лист и создаем наши
        wb.remove(wb.active)

        # Лист 1: Сводка
        summary_ws = wb.create_sheet("Сводка")

        # Заголовок
        summary_ws['A1'] = f"Отчет BionicPRO для пользователя {user_id}"
        summary_ws['A1'].font = Font(size=16, bold=True)
        summary_ws['A1'].alignment = Alignment(horizontal='center')
        summary_ws.merge_cells('A1:D1')

        # Период отчета
        summary_ws['A3'] = "Период:"
        summary_ws['B3'] = f"{reports_data.get('period', {}).get('start_date', '')} - {reports_data.get('period', {}).get('end_date', '')}"
        summary_ws['A3'].font = Font(bold=True)

        # Данные сводки
        summary = reports_data.get('summary', {})
        row = 5
        metrics = [
            ("Всего дней с данными:", summary.get('total_days', 0)),
            ("Общее время использования (часы):", summary.get('total_usage_hours', 0)),
            ("Средняя эффективность движения (%):", summary.get('avg_movement_efficiency', 0)),
            ("Средняя оценка обслуживания:", summary.get('avg_maintenance_score', 0)),
            ("Средний уровень батареи (%):", summary.get('avg_battery_health', 0)),
            ("Всего аномалий:", summary.get('total_anomalies', 0)),
            ("Всего сессий:", summary.get('total_sessions', 0))
        ]

        for metric_name, metric_value in metrics:
            summary_ws[f'A{row}'] = metric_name
            summary_ws[f'B{row}'] = metric_value
            summary_ws[f'A{row}'].font = Font(bold=True)
            row += 1

        # Лист 2: Детальные данные
        details_ws = wb.create_sheet("Детальные данные")

        # Заголовки колонок
        headers = ["Дата", "Устройство", "Время использования (ч)", "Эффективность (%)",
                  "Обслуживание", "Батарея (%)", "Аномалии", "Сессии"]
        for idx, header in enumerate(headers, 1):
            cell = details_ws.cell(row=1, column=idx, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.font = Font(color="FFFFFF", bold=True)

        # Данные
        daily_reports = reports_data.get('daily_reports', [])
        for row_idx, report in enumerate(daily_reports, 2):
            details_ws.cell(row=row_idx, column=1, value=report.get('report_date', ''))
            details_ws.cell(row=row_idx, column=2, value=report.get('device_id', ''))
            details_ws.cell(row=row_idx, column=3, value=report.get('daily_usage_hours', 0))
            details_ws.cell(row=row_idx, column=4, value=report.get('movement_efficiency', 0))
            details_ws.cell(row=row_idx, column=5, value=report.get('maintenance_score', 0))
            details_ws.cell(row=row_idx, column=6, value=report.get('battery_health', 0))
            details_ws.cell(row=row_idx, column=7, value=report.get('anomaly_count', 0))
            details_ws.cell(row=row_idx, column=8, value=report.get('total_sessions', 0))

        # Автоматическая ширина колонок
        for ws in [summary_ws, details_ws]:
            for column in ws.columns:
                max_length = 0
                column_letter = None
                for cell in column:
                    try:
                        # Проверяем, что это не merged cell
                        if hasattr(cell, 'column_letter'):
                            column_letter = cell.column_letter
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                if column_letter:
                    adjusted_width = min(max_length + 2, 50)
                    ws.column_dimensions[column_letter].width = adjusted_width

        # Сохраняем в память
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        # Возвращаем файл
        from flask import Response

        response = Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename=bionicpro_report_{user_id}.xlsx'
            }
        )
        return response

    except Exception as e:
        logger.error(f"❌ Error generating Excel report: {e}")
        return jsonify({
            'error': 'Failed to generate Excel report',
            'message': str(e)
        }), 500

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

        # Функция для безопасной обработки числовых значений, включая NaN
        def safe_float(value, default=0.0):
            try:
                if value is None:
                    return default
                result = float(value)
                # Проверяем на NaN и бесконечность
                if result != result or result == float('inf') or result == float('-inf'):
                    return default
                return result
            except (ValueError, TypeError):
                return default

        summary = {
            'user_id': user_id,
            'period_days': 30,
            'total_days_with_data': int(row[0]),
            'total_usage_hours': safe_round(safe_float(row[1]), 2),
            'avg_movement_efficiency': safe_round(safe_float(row[2]), 1),
            'avg_maintenance_score': safe_round(safe_float(row[3]), 1),
            'avg_battery_health': safe_round(safe_float(row[4]), 1),
            'total_anomalies': int(row[5] or 0),
            'total_sessions': int(row[6] or 0),
            'last_activity': row[7].isoformat() if row[7] else None
        }

        # Очищаем данные от возможных NaN значений перед отправкой
        cleaned_summary = clean_nan_values(summary)
        return jsonify(cleaned_summary)

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