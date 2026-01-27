# BionicPRO Reports API Backend

Python Flask API для предоставления персональных отчетов пользователям о работе их бионических протезов.

## Функциональность

✅ **Извлечение отчетов из OLAP (ClickHouse)** - оптимизированные запросы к витрине данных
✅ **Row-Level Security** - пользователи видят только свои данные
✅ **JWT аутентификация** - безопасный доступ с токенами
✅ **Redis кеширование** - быстрый отклик для повторных запросов
✅ **Rate limiting** - защита от злоупотреблений
✅ **Аудит доступа** - логирование всех обращений к данным
✅ **Comprehensive API** - полный набор endpoints для отчетов

## Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React App     │───▶│  Reports API    │───▶│   ClickHouse    │
│  (Frontend)     │    │   (Backend)     │    │   (OLAP DB)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       ▲
                                │                       │
                                ▼                       │
                       ┌─────────────────┐              │
                       │     Redis       │              │
                       │   (Cache)       │              │
                       └─────────────────┘              │
                                                        │
                       ┌─────────────────┐              │
                       │   Airflow ETL   │─────────────▶│
                       │  (Data Pipeline)│              │
                       └─────────────────┘              │
```

### Основные компоненты:

1. **Flask API** - REST endpoints для отчетов
2. **JWT Auth** - аутентификация пользователей
3. **ClickHouse Client** - подключение к OLAP базе
4. **Redis Cache** - кеширование отчетов
5. **Row-Level Security** - изоляция данных пользователей

## Быстрый старт

### 1. Установка зависимостей

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
# Скопируйте и настройте переменные
cp .env.example .env
```

### 3. Запуск для разработки

```bash
# Локальный запуск
python app.py

# Или с автоперезагрузкой
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

### 4. Запуск с Docker

```bash
# Сборка образа
docker build -t bionicpro-reports-api .

# Запуск контейнера
docker run -p 5000:5000 \
  -e CLICKHOUSE_HOST=localhost \
  -e REDIS_HOST=localhost \
  bionicpro-reports-api

# Или через docker-compose
docker-compose up -d
```

### 5. Интеграция с полной системой

```bash
# Запуск вместе с ETL и базами данных
cd ..
docker-compose -f airflow-docker-compose.yml up -d
```

## API Endpoints

### Аутентификация

```http
POST /auth/login
Content-Type: application/json

{
  "username": "user1",
  "password": "password123"
}
```

### Получение отчетов

```http
GET /reports/{user_id}?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {jwt_token}
```

### Краткая сводка

```http
GET /reports/{user_id}/summary
Authorization: Bearer {jwt_token}
```

### Список устройств

```http
GET /reports/{user_id}/devices
Authorization: Bearer {jwt_token}
```

Полная документация: [API_Documentation.md](./API_Documentation.md)

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `CLICKHOUSE_HOST` | ClickHouse сервер | localhost |
| `CLICKHOUSE_PORT` | ClickHouse порт | 8123 |
| `CLICKHOUSE_DB` | База данных | bionicpro |
| `CLICKHOUSE_USER` | Пользователь | reports_user |
| `CLICKHOUSE_PASSWORD` | Пароль | (обязательно) |
| `REDIS_HOST` | Redis сервер | localhost |
| `REDIS_PORT` | Redis порт | 6379 |
| `JWT_SECRET_KEY` | Секретный ключ JWT | (обязательно) |
| `ADMIN_USERS` | Список админов | admin |

### Подключения к базам данных

API автоматически инициализирует подключения при старте:

```python
# ClickHouse для отчетов
clickhouse_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)

# Redis для кеширования
redis_client = redis.Redis(**REDIS_CONFIG)
```

## Безопасность

### Row-Level Security

Все запросы автоматически фильтруются по пользователю:

```sql
-- Автоматически добавляется к каждому запросу
WHERE user_id = '{current_user_id}'
```

### JWT Authentication

```python
@jwt_required()
@require_user_access
def get_user_reports(user_id):
    # Проверка доступа на уровне декораторов
    current_user = get_jwt_identity()
    if current_user != user_id:
        return 403  # Forbidden
```

### Защита от SQL инъекций

Все параметры экранируются:

```python
query = f"SELECT * FROM reports WHERE user_id = '{user_id}'"  # user_id проверен
```

### Rate Limiting

Nginx настроен на ограничения:
- 10 запросов/сек для общих API
- 5 запросов/сек для отчетов

## Производительность

### Кеширование в Redis

```python
# TTL 1 час для отчетов
cache_key = f"user_report:{user_id}:{start_date}:{end_date}"
redis_client.setex(cache_key, 3600, json.dumps(data))
```

### Оптимизированные запросы ClickHouse

```sql
-- Использование партиций и индексов
SELECT * FROM reports.user_analytics
WHERE user_id = 'user1'
  AND report_date >= '2024-01-01'
ORDER BY report_date DESC
LIMIT 1000
```

### Мониторинг производительности

```python
# Логирование медленных запросов
start_time = time.time()
result = clickhouse_client.query(query)
duration = time.time() - start_time

if duration > 5:  # Больше 5 секунд
    logger.warning(f"Slow query: {duration:.2f}s - {query[:100]}")
```

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# Конкретный модуль
pytest tests/test_app.py

# С покрытием
pytest --cov=app tests/
```

### Тестовые данные

```python
# Мокирование ClickHouse
@patch('app.clickhouse_client')
def test_get_reports(mock_ch):
    mock_ch.query.return_value = Mock(
        result_rows=[('2024-01-15', 'device1', 8.5, 85.2)],
        column_names=['report_date', 'device_id', 'usage', 'efficiency']
    )
```

## Деплой

### Production с Docker

```bash
# Сборка production образа
docker build -t bionicpro-reports-api:latest .

# Запуск с production настройками
docker run -d \
  --name bionicpro-api \
  -p 5000:5000 \
  -e FLASK_ENV=production \
  -e JWT_SECRET_KEY=$(openssl rand -base64 32) \
  -e CLICKHOUSE_HOST=your-clickhouse-host \
  -e REDIS_HOST=your-redis-host \
  bionicpro-reports-api:latest
```

### Production с Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bionicpro-reports-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bionicpro-reports-api
  template:
    metadata:
      labels:
        app: bionicpro-reports-api
    spec:
      containers:
      - name: api
        image: bionicpro-reports-api:latest
        ports:
        - containerPort: 5000
        env:
        - name: CLICKHOUSE_HOST
          value: "clickhouse-service"
        - name: REDIS_HOST
          value: "redis-service"
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: jwt-secret
```

### Production с reverse proxy

```nginx
# nginx.conf для production
upstream api_backend {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;  # Для load balancing
}

server {
    listen 443 ssl http2;
    server_name api.bionicpro.com;

    location /api/ {
        proxy_pass http://api_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Мониторинг

### Health Check

```bash
# Проверка состояния API
curl http://localhost:5000/health

# Ответ при успехе
{
  "status": "healthy",
  "services": {
    "clickhouse": "OK",
    "redis": "OK"
  }
}
```

### Логи

```bash
# Логи приложения
tail -f logs/app.log

# Логи Docker контейнера
docker logs bionicpro-reports-api

# Структурированные логи
{
  "timestamp": "2024-01-31T12:00:00",
  "level": "INFO",
  "message": "📊 Getting reports for user user1",
  "user_id": "user1",
  "ip": "192.168.1.100"
}
```

### Метрики для Prometheus

```python
# app.py уже включает метрики
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('api_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('api_request_duration_seconds', 'Request latency')

@REQUEST_LATENCY.time()
def get_reports():
    REQUEST_COUNT.inc()
    # логика API
```

## Интеграция с Frontend

### React интеграция

```typescript
// frontend/src/services/reportsApi.ts
export async function getUserReports(
  userId: string,
  token: string,
  filters: ReportFilters
): Promise<UserReports> {
  const params = new URLSearchParams({
    start_date: filters.startDate,
    end_date: filters.endDate,
    ...(filters.deviceId && { device_id: filters.deviceId })
  });

  const response = await fetch(
    `${API_BASE_URL}/reports/${userId}?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (!response.ok) {
    throw new Error('Failed to fetch reports');
  }

  return response.json();
}
```

### Обновление ReportPage.tsx

```typescript
// Замените существующую загрузку отчета
const downloadReport = async () => {
  if (!keycloak?.token) {
    setError('Not authenticated');
    return;
  }

  try {
    setLoading(true);
    setError(null);

    const reports = await getUserReports(
      keycloak.tokenParsed?.sub || 'current_user',
      keycloak.token,
      {
        startDate: '2024-01-01',
        endDate: new Date().toISOString().split('T')[0]
      }
    );

    // Обработка полученных отчетов
    console.log('Reports received:', reports);

  } catch (err) {
    setError(err instanceof Error ? err.message : 'An error occurred');
  } finally {
    setLoading(false);
  }
};
```

## Разработка

### Структура проекта

```
backend/
├── app.py                 # Основное приложение
├── requirements.txt       # Зависимости Python
├── Dockerfile            # Контейнеризация
├── docker-compose.yml    # Локальная разработка
├── nginx.conf           # Reverse proxy
├── .env.example         # Пример конфигурации
├── API_Documentation.md # Документация API
├── tests/              # Тесты
│   └── test_app.py
└── logs/               # Логи приложения
```

### Добавление нового endpoint

1. Создайте функцию в `app.py`:

```python
@app.route('/reports/<user_id>/analytics', methods=['GET'])
@jwt_required()
@require_user_access
def get_user_analytics(user_id):
    # Ваша логика
    return jsonify(data)
```

2. Добавьте тесты:

```python
def test_get_user_analytics(client, auth_headers):
    response = client.get('/reports/user1/analytics', headers=auth_headers)
    assert response.status_code == 200
```

3. Обновите документацию в `API_Documentation.md`

## Устранение неполадок

### Типичные проблемы

1. **ClickHouse connection failed**
   ```bash
   # Проверьте подключение
   docker exec clickhouse clickhouse-client --query="SELECT 1"
   ```

2. **Redis connection failed**
   ```bash
   # Проверьте Redis
   docker exec redis redis-cli ping
   ```

3. **JWT token expired**
   ```bash
   # Получите новый токен через /auth/login
   ```

### Отладка

```python
# Включите debug логи
import logging
logging.basicConfig(level=logging.DEBUG)

# Или через переменную окружения
export FLASK_ENV=development
python app.py
```

## Лицензия

Проприетарное ПО BionicPRO. Все права защищены.