# BionicPRO Reports API Documentation

REST API для получения персональных отчетов о работе бионических протезов из OLAP-базы ClickHouse.

## Базовая информация

- **Base URL**: `http://localhost:5000` (development)
- **Authentication**: JWT Bearer tokens
- **Content-Type**: `application/json`
- **Rate Limits**: 10 requests/second для общих API, 5 requests/second для отчетов

## Аутентификация

### POST /auth/login

Получение JWT токена для доступа к API.

**Request Body:**
```json
{
  "username": "user1",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": "user1",
  "expires_in": 86400
}
```

**Response (401 Unauthorized):**
```json
{
  "error": "Invalid credentials"
}
```

## Отчеты пользователей

Все endpoints отчетов требуют JWT аутентификации и применяют Row-Level Security - пользователь может получить только свои данные.

### GET /reports/{user_id}

Получение детальных отчетов пользователя за период.

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Query Parameters:**
- `start_date` (optional): начальная дата в формате YYYY-MM-DD (по умолчанию: -30 дней)
- `end_date` (optional): конечная дата в формате YYYY-MM-DD (по умолчанию: сегодня)
- `device_id` (optional): фильтр по конкретному устройству
- `format` (optional): json|pdf|excel (по умолчанию: json)

**Example Request:**
```http
GET /reports/user1?start_date=2024-01-01&end_date=2024-01-31&device_id=esp32-001
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Response (200 OK):**
```json
{
  "user_id": "user1",
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "cached": false,
  "summary": {
    "total_days": 31,
    "total_usage_hours": 248.5,
    "avg_movement_efficiency": 87.2,
    "avg_maintenance_score": 89.1,
    "avg_battery_health": 91.5,
    "total_anomalies": 12,
    "total_sessions": 465
  },
  "trends": {
    "usage_trend": "improving",
    "efficiency_trend": "stable",
    "battery_trend": "declining"
  },
  "recommendations": [
    {
      "type": "battery",
      "priority": "medium",
      "title": "Снижение здоровья батареи",
      "message": "Рекомендуется проверить состояние батареи",
      "action": "Schedule battery check"
    }
  ],
  "daily_reports": [
    {
      "report_date": "2024-01-31",
      "device_id": "esp32-001",
      "daily_usage_hours": 8.2,
      "movement_efficiency": 88.5,
      "maintenance_score": 91.2,
      "battery_health": 89.7,
      "anomaly_count": 1,
      "total_sessions": 15,
      "avg_session_duration": 32.8,
      "max_pressure_reached": 456.2,
      "last_sync": "2024-01-31T18:45:32"
    }
  ]
}
```

### GET /reports/{user_id}/devices

Получение списка устройств пользователя.

**Response (200 OK):**
```json
{
  "user_id": "user1",
  "devices": [
    {
      "device_id": "esp32-001",
      "last_report_date": "2024-01-31",
      "total_reports": 120
    },
    {
      "device_id": "esp32-002",
      "last_report_date": "2024-01-30",
      "total_reports": 89
    }
  ]
}
```

### GET /reports/{user_id}/summary

Получение краткой сводки за последние 30 дней.

**Response (200 OK):**
```json
{
  "user_id": "user1",
  "period_days": 30,
  "total_days_with_data": 28,
  "total_usage_hours": 224.8,
  "avg_movement_efficiency": 86.7,
  "avg_maintenance_score": 88.9,
  "avg_battery_health": 90.2,
  "total_anomalies": 8,
  "total_sessions": 420,
  "last_activity": "2024-01-31T18:45:32"
}
```

## Системные endpoints

### GET /health

Проверка состояния API и подключений к базам данных.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-31T12:00:00",
  "services": {
    "clickhouse": "OK",
    "redis": "OK"
  }
}
```

## Коды ошибок

### 400 Bad Request
Неверные параметры запроса.
```json
{
  "error": "Invalid request parameters",
  "message": "start_date must be in YYYY-MM-DD format"
}
```

### 401 Unauthorized
Отсутствует или неверный JWT токен.
```json
{
  "error": "Unauthorized access",
  "message": "Valid JWT token required"
}
```

### 403 Forbidden
Попытка доступа к чужим данным.
```json
{
  "error": "Access denied",
  "message": "You can only access your own reports"
}
```

### 404 Not Found
Несуществующий endpoint.
```json
{
  "error": "Endpoint not found"
}
```

### 429 Too Many Requests
Превышен лимит запросов.
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests, please try again later"
}
```

### 500 Internal Server Error
Внутренняя ошибка сервера.
```json
{
  "error": "Internal server error",
  "message": "Failed to retrieve reports"
}
```

### 503 Service Unavailable
Недоступность внешних сервисов.
```json
{
  "error": "Service temporarily unavailable",
  "message": "Database connection failed"
}
```

## Безопасность

### Row-Level Security (RLS)
- Все запросы к данным фильтруются по `user_id` текущего пользователя
- Администраторы имеют доступ ко всем данным
- SQL инъекции предотвращаются параметризованными запросами

### Аутентификация и авторизация
- JWT токены с истечением через 24 часа
- Обязательная аутентификация для всех endpoints кроме `/health` и `/auth/login`
- Проверка доступа на уровне маршрутов

### HTTPS и заголовки безопасности
- Обязательное использование HTTPS в production
- Security headers: X-Frame-Options, X-Content-Type-Options, etc.
- CORS настроен только для разрешенных origin

### Аудит
- Логирование всех обращений к отчетам
- Хранение логов доступа в Redis для дальнейшей обработки ETL
- Мониторинг подозрительной активности

## Rate Limiting

- **Общие API**: 10 запросов/секунду на IP
- **Отчеты**: 5 запросов/секунду на IP для `/reports/*`
- **Burst**: до 20 одновременных запросов
- **Период блокировки**: 60 секунд при превышении

## Кеширование

- **Redis TTL**: 1 час для отчетов
- **Cache key**: `user_report:{user_id}:{start_date}:{end_date}:{device_id}`
- **Invalidation**: автоматическое по TTL
- **Cache hit headers**: `"cached": true` в ответе

## Мониторинг

### Метрики (Prometheus)
- `api_requests_total` - общее количество запросов
- `api_request_duration_seconds` - время обработки запросов
- `api_errors_total` - количество ошибок по типам
- `cache_hits_total` / `cache_misses_total` - эффективность кеша

### Health Checks
- **Endpoint**: `/health`
- **Интервал**: каждые 30 секунд
- **Таймаут**: 10 секунд
- **Проверки**: ClickHouse, Redis подключения

## Примеры использования

### JavaScript (Frontend)
```javascript
// Аутентификация
const authResponse = await fetch('/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'user1',
    password: 'password123'
  })
});

const { access_token } = await authResponse.json();

// Получение отчетов
const reportsResponse = await fetch('/reports/user1?start_date=2024-01-01', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  }
});

const reports = await reportsResponse.json();
console.log('Reports:', reports);
```

### Python (Client)
```python
import requests

# Аутентификация
auth_response = requests.post('/auth/login', json={
    'username': 'user1',
    'password': 'password123'
})
token = auth_response.json()['access_token']

# Получение отчетов
headers = {'Authorization': f'Bearer {token}'}
reports_response = requests.get(
    '/reports/user1?start_date=2024-01-01',
    headers=headers
)

reports = reports_response.json()
print(f"Total usage: {reports['summary']['total_usage_hours']} hours")
```

### cURL
```bash
# Аутентификация
TOKEN=$(curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"password123"}' \
  | jq -r '.access_token')

# Получение отчетов
curl -X GET "http://localhost:5000/reports/user1?start_date=2024-01-01" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

## Интеграция с Frontend

API спроектирован для интеграции с React приложением из `sprint9/frontend`:

1. **CORS**: Настроен для `http://localhost:3000`
2. **JWT**: Совместим с существующим Keycloak
3. **Error handling**: Структурированные ошибки для UI
4. **Loading states**: Поддержка прогрессивной загрузки
5. **Caching**: Снижение нагрузки на сервер

Для интеграции обновите `ReportPage.tsx`:

```typescript
// В процессе загрузки отчета
const response = await fetch(`${process.env.REACT_APP_API_URL}/reports/${userId}`, {
  headers: {
    'Authorization': `Bearer ${keycloak.token}`
  }
});

if (response.ok) {
  const reports = await response.json();
  // Обработка данных отчета
} else {
  // Обработка ошибок
}
```