# 🚀 Инструкция по запуску BionicPRO (Обновленная версия)

> 🆕 **Важное обновление**: Docker Compose файлы объединены! Теперь запуск всех сервисов происходит одной командой.

## 🔄 Шаг 0: Получение проекта

### Клонирование репозитория
```bash
git clone <repository-url>
cd architecture-bionicpro
```

### Проверка структуры (обновленная)
Убедитесь в наличии файлов:
- ✅ `docker-compose.yaml` - **ЕДИНЫЙ файл** со всеми сервисами
- ✅ `.env.example` - шаблон переменных окружения
- ✅ `unified-docker-compose-guide.md` - документация по объединенной конфигурации
- ✅ папки: `frontend/`, `backend/`, `keycloak/`, `sql/`, `dags/`, `logs/`, `plugins/`

## 📋 Предварительные требования

### Системные требования (обновленные)
- **Docker** версии 24.0+
- **Docker Compose** версии 2.20+
- **Свободная RAM**: минимум 12GB (для всех сервисов)
- **Свободное место**: минимум 15GB
- **Порты**: 3000, 5000, 5433, 5434, 6380, 8080, 8081, 8123, 9000, 9092

### Проверка готовности
```bash
# Проверить версии Docker
docker --version
docker-compose --version

# Проверить доступные ресурсы
docker system df
docker system info | grep -i memory
```

## 🔧 Шаг 1: Подготовка окружения

### 1.1 Настройка переменных окружения ⚡ (КРИТИЧЕСКИ ВАЖНО!)

```bash
cd architecture-bionicpro

# Создать файл переменных окружения из шаблона
cp .env.example .env
```

### 🔑 Настройка JWT_SECRET_KEY
**JWT_SECRET_KEY** - секретный ключ для подписи JWT токенов аутентификации.

**Способы генерации:**
```bash
# Способ 1: OpenSSL (рекомендуется)
openssl rand -hex 32

# Способ 2: Python
python -c "import secrets; print(secrets.token_hex(32))"

# Способ 3: Online генератор (только для разработки!)
# Идите на https://jwt.io/ → Generate random key
```

**Пример результата:**
```
a4f8b2c1d5e9f7a3b8c2d6e0f4a7b1c5d8e2f6a0b4c8d2e6f0a4b8c1d5e9f7a3
```

### 🔗 Настройка BITRIX24_WEBHOOK_URL

**Где получить Webhook URL для Bitrix24:**

1. **Войти в Bitrix24:**
   - Откройте ваш портал Bitrix24 (например: `https://mycompany.bitrix24.com`)
   - Войдите под администратором

2. **Создать Webhook:**
   ```
   Приложения → Разработчикам → Вебхуки → Входящий вебхук
   ```

3. **Настроить разрешения:**
   ```
   ✅ CRM (crm) - чтение/запись контактов и сделок
   ✅ Списки (lists) - чтение данных
   ✅ Пользователи (user) - чтение информации о пользователях
   ```

4. **Скопировать URL:**
   ```
   Пример: https://mycompany.bitrix24.com/rest/1/abc123xyz789/
   ```

**Альтернатива для тестирования:**
Если у вас нет Bitrix24, можно использовать заглушку:
```bash
BITRIX24_WEBHOOK_URL=https://jsonplaceholder.typicode.com/posts/
```

### 📝 Пример полностью настроенного .env файла:
```bash
# Airflow Configuration
AIRFLOW_UID=50000
AIRFLOW_PROJ_DIR=.

# JWT Security - СГЕНЕРИРОВАТЬ НОВЫЙ!
JWT_SECRET_KEY=a4f8b2c1d5e9f7a3b8c2d6e0f4a7b1c5d8e2f6a0b4c8d2e6f0a4b8c1d5e9f7a3

# Database Passwords - ИЗМЕНИТЬ НА НАДЕЖНЫЕ!
POSTGRES_KEYCLOAK_PASSWORD=MySecureKeycloakDB2024!
POSTGRES_AIRFLOW_PASSWORD=MySecureAirflowDB2024!
CLICKHOUSE_PASSWORD=MySecureClickhousePassword2024!
REDIS_PASSWORD=MySecureRedisPassword2024!

# External APIs - ПОЛУЧИТЬ ИЗ BITRIX24
BITRIX24_WEBHOOK_URL=https://mycompany.bitrix24.com/rest/1/abc123xyz789/

# Admin Users (comma-separated)
ADMIN_USERS=admin,admin@bionicpro.com

# Environment flags
FLASK_ENV=production
NODE_ENV=production
DEBUG=false
```

### ⚠️ КРИТИЧЕСКИ ВАЖНО:
- **НИКОГДА** не коммитьте `.env` файл в Git
- **ОБЯЗАТЕЛЬНО** генерируйте новый `JWT_SECRET_KEY` для каждой установки
- Используйте **надежные уникальные пароли** для всех сервисов

## 🚀 Шаг 2: Единый запуск всех сервисов (НОВОЕ!)
### 2.1 Запуск ВСЕХ сервисов одной командой
```bash
# Запуск всего стека BionicPRO
docker-compose up -d

# Проверка статуса всех сервисов
docker-compose ps
```

**Ожидаемые сервисы (11 контейнеров):**

| Сервис | Контейнер | Порт | Статус |
|--------|-----------|------|--------|
| **Frontend** | bionicpro-frontend | 3000 | Up |
| **Keycloak** | bionicpro-keycloak | 8080 | Up |
| **Keycloak DB** | bionicpro-keycloak-db | 5433 | Up (healthy) |
| **Airflow Web** | bionicpro-airflow-webserver | 8081 | Up (healthy) |
| **Airflow Scheduler** | bionicpro-airflow-scheduler | - | Up (healthy) |
| **Airflow DB** | bionicpro-postgres-airflow | 5434 | Up (healthy) |
| **ClickHouse** | bionicpro-clickhouse | 8123,9000 | Up (healthy) |
| **Redis** | bionicpro-redis | 6380 | Up (healthy) |
| **Reports API** | bionicpro-reports-api | 5000 | Up (healthy) |
| **Kafka** | bionicpro-kafka | 9092 | Up |
| **Zookeeper** | bionicpro-zookeeper | 2181 | Up |

### 2.2 Автоматический тест всех сервисов
```bash
# Windows - Быстрый тест всех сервисов
checks\test-services.bat

# Windows - Краткая диагностика с подсчетом успешных/неудачных тестов
checks\quick-health-check.bat

# Windows - Полная проверка здоровья системы (включая БД, логи, сети)
checks\health-check-full.bat

# Linux/macOS
curl http://localhost:8080/realms/reports-realm && echo " ✅ Keycloak OK"
curl http://localhost:8081/health && echo " ✅ Airflow OK"
curl http://localhost:8123/ping && echo " ✅ ClickHouse OK"
curl http://localhost:3000 && echo " ✅ Frontend OK"
curl http://localhost:5000/health && echo " ✅ Reports API OK"
```

### 2.3 Пошаговый мониторинг запуска
```bash
# 1. Мониторинг в реальном времени
docker-compose up

# 2. Или запуск в фоне с мониторингом логов
docker-compose up -d
docker-compose logs -f

# 3. Проверка healthcheck'ов
watch docker-compose ps
```

### 📊 Порядок запуска (автоматический):
1. **Базы данных** → `postgres-airflow`, `keycloak-db`
2. **Кеширование** → `redis`
3. **Аналитика** → `clickhouse`
4. **Очереди** → `zookeeper` → `kafka`
5. **Инициализация** → `airflow-init` ⏳
6. **Основные сервисы** → `keycloak`, `frontend`, `reports-api`
7. **Airflow UI** → `airflow-webserver`, `airflow-scheduler`

## 🏥 Шаг 3: Проверка здоровья системы

### 3.1 Обновленные endpoints для проверки
```bash
# Правильные URL для проверки (обновлено!)
curl http://localhost:3000                                       # Frontend
curl http://localhost:8080/realms/reports-realm                  # Keycloak (БЕЗ /auth/)
curl http://localhost:8081/health                                # Airflow
curl http://localhost:5000/health                                # Reports API
curl http://localhost:8123/ping                                  # ClickHouse

# Ожидаемые ответы:
# Keycloak: {"realm":"reports-realm","public_key":"..."}
# Airflow: {"metadatabase":{"status":"healthy"}...}
# ClickHouse: Ok.
```

### 3.2 Упрощенная проверка логов
```bash
# Все логи из единого файла
docker-compose logs [service_name]

# Примеры конкретных сервисов:
docker-compose logs keycloak
docker-compose logs clickhouse
docker-compose logs reports-api
docker-compose logs airflow-scheduler
docker-compose logs airflow-webserver

# Логи в реальном времени
docker-compose logs -f keycloak
```

### 3.3 Проверка баз данных (обновлено)
```bash
# ClickHouse (обновленная команда)
docker-compose exec clickhouse clickhouse-client --query "SHOW DATABASES"

# PostgreSQL (Airflow)
# Примечание: Если вы изменили пароль в .env, команда может запросить пароль
docker-compose exec postgres-airflow psql -U airflow -d airflow -c "\\dt"

# PostgreSQL (Keycloak)
# Примечание: Если вы изменили пароль в .env, команда может запросить пароль
docker-compose exec keycloak_db psql -U keycloak_user -d keycloak_db -c "\\dt"

# Redis (с паролем - используйте пароль из .env файла)
# Если используете дефолтный пароль:
docker-compose exec redis redis-cli -a bionicpro_redis_password ping
# Если установили свой пароль в .env, замените его в команде:
# docker exec -it bionicpro-redis redis-cli -a ваш_redis_пароль ping
```

## 📊 Шаг 4: Инициализация данных и тестирование

### 4.1 Создание тестовых данных в ClickHouse
```bash
# Подключение к ClickHouse для создания тестовых данных
docker exec -it bionicpro-clickhouse clickhouse-client --query "
-- Создание тестовых данных для демонстрации
USE bionicpro;

-- Создание таблицы отчётов если не существует
CREATE TABLE IF NOT EXISTS reports.user_analytics (
    user_id String,
    device_id String,
    report_date Date,
    daily_usage_hours Float32,
    movement_efficiency Float32,
    maintenance_score Float32,
    battery_health Float32,
    anomaly_count UInt32,
    total_sessions UInt32,
    avg_session_duration Float32,
    max_pressure_reached Float32,
    last_sync DateTime,
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, device_id, report_date)
SETTINGS index_granularity = 8192;

-- Вставка тестовых данных
INSERT INTO reports.user_analytics VALUES
    ('user1', 'ESP32-001-BP', '2024-01-15', 8.5, 87.2, 92.1, 89.3, 2, 12, 42.5, 850.0, '2024-01-15 23:45:00', now(), now()),
    ('user1', 'ESP32-001-BP', '2024-01-16', 7.2, 85.1, 90.8, 87.1, 1, 10, 43.2, 820.0, '2024-01-16 23:30:00', now(), now()),
    ('user1', 'ESP32-001-BP', '2024-01-17', 6.8, 88.5, 93.2, 91.5, 0, 9, 45.3, 780.0, '2024-01-17 22:15:00', now(), now()),
    ('user2', 'ESP32-002-BP', '2024-01-15', 5.5, 75.2, 85.1, 78.3, 4, 8, 41.0, 920.0, '2024-01-15 23:20:00', now(), now()),
    ('user2', 'ESP32-002-BP', '2024-01-16', 6.2, 77.8, 87.5, 80.1, 2, 10, 37.2, 880.0, '2024-01-16 22:45:00', now(), now());
"
```

### 4.2 Проверка доступности тестовых данных
```bash
# Проверка данных в ClickHouse
docker exec -it bionicpro-clickhouse clickhouse-client --query "
SELECT
    user_id,
    device_id,
    count() as report_count,
    min(report_date) as first_date,
    max(report_date) as last_date
FROM reports.user_analytics
GROUP BY user_id, device_id
ORDER BY user_id, device_id;
"
```

## 🧪 Шаг 5: Полное тестирование функциональности

### 5.1 Тестирование аутентификации
1. **Откройте браузер** → http://localhost:3000
2. **Нажмите "Войти через Keycloak"**
3. **В Keycloak введите**:
   - Username: `testuser` или создайте пользователя в Keycloak Admin
   - Password: `password`
4. **Проверьте перенаправление** обратно в приложение

### 5.2 Создание тестового пользователя в Keycloak
```bash
# Доступ к Keycloak Admin Console
echo "Откройте: http://localhost:8080/admin"
echo "Логин: admin"
echo "Пароль: admin"

echo "1. Перейдите в realm 'reports-realm'"
echo "2. Users → Add user"
echo "3. Username: user1, Email: user1@test.com"
echo "4. Credentials → Set password: password123"
echo "5. Temporary: OFF"
echo "6. Save"
```

### 5.3 Тестирование API отчётов
```bash
# 1. Получить JWT токен
JWT_TOKEN=$(curl -s -X POST http://localhost:5000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"user1","password":"password123"}' | \\
  jq -r '.access_token')

echo "JWT Token: $JWT_TOKEN"

# 2. Проверить доступность отчётов
curl -H "Authorization: Bearer $JWT_TOKEN" \\
     "http://localhost:5000/reports/user1?start_date=2024-01-15&end_date=2024-01-17&format=json" | \\
     jq '.'

# 3. Проверить список устройств
curl -H "Authorization: Bearer $JWT_TOKEN" \\
     "http://localhost:5000/reports/user1/devices" | \\
     jq '.'

# 4. Проверить сводку
curl -H "Authorization: Bearer $JWT_TOKEN" \\
     "http://localhost:5000/reports/user1/summary" | \\
     jq '.'
```

### 5.4 Тестирование безопасности
```bash
# 1. Попытка доступа без токена (должна вернуть 401)
curl -I "http://localhost:5000/reports/user1"

# 2. Попытка доступа к чужим данным (должна вернуть 403)
curl -H "Authorization: Bearer $JWT_TOKEN" \\
     "http://localhost:5000/reports/user2" | \\
     jq '.'

# 3. Проверка валидации периода данных
curl -H "Authorization: Bearer $JWT_TOKEN" \\
     "http://localhost:5000/reports/user1?start_date=2024-12-01&end_date=2024-12-31" | \\
     jq '.'
```

## 🎯 Шаг 6: Тестирование UI функциональности

### 6.1 Обзор UI компонентов

#### Основные компоненты интерфейса:
- **ReportPage** (`frontend/src/components/ReportPage.tsx`) - основная страница отчётов
- **UserSummary** (`frontend/src/components/UserSummary.tsx`) - сводка пользователя за 30 дней
- **ReportPreview** (`frontend/src/components/ReportPreview.tsx`) - детальное отображение отчётов

#### Функциональность интерфейса:
- ✅ **Аутентификация через Keycloak** с автоматическим обновлением JWT токенов
- ✅ **Строгий контроль доступа** - пользователи видят только свои данные
- ✅ **Выбор периода и фильтрация** по устройствам
- ✅ **Экспорт в разных форматах** (JSON, PDF, Excel)
- ✅ **Адаптивный дизайн** для мобильных устройств
- ✅ **Цветовые индикаторы состояния** и тренды показателей

### 6.2 Браузерное тестирование
1. **Перейдите на** http://localhost:3000
2. **Войдите как user1** через Keycloak
3. **Проверьте сводку пользователя** (должна загрузиться автоматически):
   - Активные дни
   - Общее время использования
   - Эффективность движений
   - Здоровье батареи
   - Техническое состояние
   - Количество аномалий
4. **Измените период дат** на 2024-01-15 → 2024-01-17
5. **Выберите устройство** или оставьте "Все устройства"
6. **Выберите формат отчёта**:
   - **JSON** - для просмотра в браузере
   - **PDF** - для печати и архивирования
   - **Excel** - для дальнейшего анализа
7. **Нажмите "Показать отчёт" или "Скачать отчёт"**
8. **Проверьте отображение данных**:
   - Сводка показателей с цветовыми индикаторами
   - Тренды (📈 улучшается, 📉 ухудшается, 📊 стабильно)
   - Рекомендации по улучшению
   - Детальная таблица ежедневных данных

### 6.3 Цветовые коды состояния
- 🟢 **Зелёный (80-100%)**: Отличное состояние
- 🟡 **Жёлтый (60-79%)**: Нормальное состояние
- 🔴 **Красный (0-59%)**: Требует внимания

### 6.4 Проверка валидации данных
1. **Выберите период**: завтра - послезавтра
2. **Нажмите "Показать отчёт"**
3. **Должно появиться сообщение**: "Данные за будущие даты недоступны"

### 6.5 Проверка безопасности в UI
1. **Откройте Developer Tools** → Network tab
2. **Сгенерируйте отчёт**
3. **Проверьте запрос**:
   - Authorization header присутствует
   - URL содержит корректный user_id
   - Параметры переданы правильно

### 6.6 Проверка обработки ошибок
UI корректно обрабатывает следующие ошибки:
- **401 Unauthorized** - автоматическое перенаправление на login
- **403 Forbidden** - сообщение "Доступ запрещён"
- **429 Rate Limited** - "Превышен лимит запросов"
- **500 Server Error** - "Внутренняя ошибка сервера"
- **Ошибки сети** - "Ошибка подключения к серверу"

### 6.7 Мобильная версия
Проверьте адаптивность интерфейса:
- Переключите в Developer Tools на мобильное отображение
- Убедитесь что все элементы доступны и удобны для использования
- Проверьте touch-friendly интерфейс (кнопки минимум 44px)

### 6.8 API Endpoints для UI
- `GET /reports/{user_id}` - получение отчёта с параметрами
- `GET /reports/{user_id}/devices` - список устройств пользователя
- `GET /reports/{user_id}/summary` - сводка пользователя

## 📊 Шаг 7: Запуск и проверка Airflow DAGs

### 7.1 Доступ к Airflow
```bash
echo "Airflow UI: http://localhost:8081"
echo "Логин: admin"
echo "Пароль: admin"
```

### 7.2 Создание и активация DAG (если есть)
1. **Перейдите в Airflow UI** http://localhost:8081
2. **Войдите**: admin / admin
3. **Найдите DAGs** (если они были добавлены в ./dags/)
4. **Активируйте DAG** переключателем
5. **Запустите вручную** кнопкой "Trigger DAG"

### 7.3 Имитация ETL обработки (если нет реальных DAGs)
```bash
# Добавление данных напрямую в ClickHouse для имитации ETL
docker exec -it bionicpro-clickhouse clickhouse-client --query "
INSERT INTO reports.user_analytics VALUES
    ('user1', 'ESP32-001-BP', today() - 1, 7.5, 86.2, 91.1, 88.3, 1, 11, 41.5, 860.0, now() - INTERVAL 1 HOUR, now(), now()),
    ('user1', 'ESP32-001-BP', today() - 2, 8.1, 89.1, 93.5, 90.2, 0, 13, 38.2, 790.0, now() - INTERVAL 25 HOUR, now(), now());
"

echo "Тестовые данные для вчера и позавчера добавлены"
```

## 🔍 Шаг 8: Полная функциональная проверка

### 8.1 Проверочный чек-лист UI

- [ ] **Аутентификация**: Вход через Keycloak работает
- [ ] **Сводка пользователя**: Загружается автоматически
- [ ] **Фильтры дат**: Работают корректно
- [ ] **Выбор устройства**: Список загружается из API
- [ ] **JSON отчёт**: Данные отображаются правильно
- [ ] **Тренды**: Показываются если данных достаточно
- [ ] **Рекомендации**: Появляются при проблемах
- [ ] **Экспорт PDF/Excel**: Кнопки работают (пока заглушки)

### 8.2 Проверочный чек-лист безопасности

- [ ] **Неаутентифицированный доступ**: Блокируется
- [ ] **Чужие данные**: Возвращается 403 Forbidden
- [ ] **Будущие даты**: Валидируются и блокируются
- [ ] **Audit logging**: Все запросы логируются в Redis
- [ ] **Token validation**: JWT токены проверяются
- [ ] **Error handling**: Ошибки отображаются корректно

### 8.3 Проверочный чек-лист API

- [ ] **Health endpoint**: `/health` возвращает статус всех сервисов
- [ ] **Reports endpoint**: `/reports/{user_id}` работает с параметрами
- [ ] **Devices endpoint**: `/reports/{user_id}/devices` возвращает список
- [ ] **Summary endpoint**: `/reports/{user_id}/summary` возвращает сводку
- [ ] **OLAP integration**: Данные берутся из ClickHouse
- [ ] **Data validation**: Проверяется обработанность Airflow

## 🔧 Диагностические скрипты (НОВОЕ!)

### Автоматические инструменты диагностики

Для упрощения диагностики и устранения проблем добавлены специальные скрипты:

#### 🚀 `checks\test-services.bat` - Быстрый тест сервисов
Проверяет доступность всех основных endpoints:
```bash
checks\test-services.bat
```
**Что проверяется:**
- ✅ Keycloak - http://localhost:8080/realms/reports-realm
- ✅ Airflow - http://localhost:8081/health
- ✅ ClickHouse - http://localhost:8123/ping
- ✅ Frontend - http://localhost:3000
- ✅ Reports API - http://localhost:5000/health

#### 📊 `checks\quick-health-check.bat` - Краткая диагностика
Быстрая проверка с подсчетом статистики:
```bash
checks\quick-health-check.bat
```
**Что включено:**
- ✅ Тест всех 5 endpoints с таймаутом
- ✅ Краткий статус Docker контейнеров
- ✅ Подсчет успешных/неудачных тестов
- ✅ Быстрые ссылки для доступа

#### 🔬 `checks\health-check-full.bat` - Полная диагностика
Глубокая проверка всех компонентов системы:
```bash
checks\health-check-full.bat
```
**Что включено:**
- ✅ **3.1**: Проверка endpoints с детальными ответами
- ✅ **3.2**: Статус Docker контейнеров и последние логи
- ✅ **3.3**: Проверка всех баз данных (ClickHouse, PostgreSQL, Redis)
- ✅ Системная информация (Docker volumes, networks, system df)

#### 🛠️ `checks\troubleshoot-check.bat` - Диагностика проблем
Автоматическая диагностика типичных проблем:
```bash
checks\troubleshoot-check.bat
```
**Что проверяется:**
- ✅ **Порты**: Проверка занятости требуемых портов
- ✅ **Память и диск**: Доступные ресурсы системы
- ✅ **Docker сети**: Состояние BionicPRO сетей
- ✅ **Переменные окружения**: Валидация .env файла
- ✅ **Контейнеры**: Поиск нездоровых контейнеров
- ✅ **Директории**: Проверка обязательных папок
- ✅ **Предложения решений**: Автоматические рекомендации

### Рекомендуемая последовательность диагностики:

1. **Ежедневная проверка**: `checks\quick-health-check.bat`
2. **При подозрении на проблемы**: `checks\health-check-full.bat`
3. **При ошибках запуска**: `checks\troubleshoot-check.bat`
4. **Для простого теста**: `checks\test-services.bat`

## 🚨 Устранение проблем

### Проблема: "AIRFLOW_UID variable is not set"
**Решение**:
```bash
# Linux/Mac
export AIRFLOW_UID=$(id -u)
echo "AIRFLOW_UID=$(id -u)" >> .env

# Windows
echo "AIRFLOW_UID=50000" >> .env
```

### Проблема: "Network bionicpro-network not found"
**Решение**:
```bash
# Создать отсутствующую сеть
docker network create bionicpro-network

# Или использовать альтернативную команду
docker network create sprint9_default
```

### Проблема: Порты заняты
**Решение**:
```bash
# Проверка занятых портов
netstat -tulpn | grep -E '(3000|5000|5433|5434|6380|8080|8081|8123|9000|9092)'

# Остановка конфликтующих сервисов
sudo systemctl stop redis
sudo systemctl stop postgresql
```

### Проблема: Не хватает памяти
**Решение**:
```bash
# Проверка доступной памяти
free -h

# Очистка Docker кэша
docker system prune -a

# Увеличение swap (Linux)
sudo swapon --show
```

### Проблема: ClickHouse не стартует
**Решение**:
```bash
# Проверка логов ClickHouse
docker-compose logs clickhouse

# Проверка файлов инициализации
ls -la sql/

# Исправление прав доступа
sudo chown -R 101:101 ./clickhouse-data/
```

### Проблема: Keycloak недоступен
**Решение**:
```bash
# Проверка статуса PostgreSQL для Keycloak
docker-compose logs keycloak_db

# Проверка импорта realm
docker-compose logs keycloak | grep import

# Проверка realm файла
ls -la keycloak/realm-export.json
```

### Проблема: Сеть недоступна между контейнерами
**Решение**:
```bash
# Проверить существующие сети
docker network ls

# Проверить подключения контейнеров к сети
docker network inspect bionicpro-network

# Если нужно, удалить и пересоздать сеть
docker network rm bionicpro-network
docker network create bionicpro-network
```

## 🎉 Шаг 9: Подтверждение работоспособности

### Успешный запуск подтверждается:

1. **✅ Все сервисы "healthy"** в `docker-compose ps`
2. **✅ UI доступен** на http://localhost:3000
3. **✅ Keycloak вход работает**
4. **✅ API возвращает данные** из ClickHouse
5. **✅ Безопасность работает** (блокируется доступ к чужим данным)
6. **✅ Валидация периодов** работает корректно

### Финальная команда проверки:
```bash
echo "=== ПРОВЕРКА ВСЕХ ENDPOINTS ==="
echo "Frontend:     http://localhost:3000"
echo "Backend API:  http://localhost:5000/health"
echo "Airflow UI:   http://localhost:8081"
echo "Keycloak:     http://localhost:8080/admin"
echo "ClickHouse:   http://localhost:8123/play"

echo "=== Система готова к использованию! ==="
```

## 📈 Современные улучшения и рекомендации

### Безопасность
- ✅ Смените все пароли по умолчанию в `.env` файле перед production
- ✅ Используйте SSL/TLS сертификаты для production deployment
- ✅ Настройте firewall для ограничения доступа к портам
- ✅ Регулярно обновляйте образы Docker до последних версий

### Performance для production
- **RAM**: Рекомендуется 16GB+ для production с полной нагрузкой
- **ClickHouse**: Настройка `max_memory_usage` и `max_threads` в конфигурации
- **Airflow**: Увеличение `parallelism` и `dag_concurrency` при необходимости
- **Docker volumes**: Используйте SSD диски для лучшей производительности

### Мониторинг
- Все health check endpoints доступны для мониторинга
- Логи всех сервисов централизованы в Docker
- Redis используется для audit logging всех API запросов

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи через `docker-compose logs [service_name]`
2. Убедитесь что все порты свободны
3. Проверьте доступность ресурсов системы
4. Обратитесь к секции устранения проблем выше

## 🆕 Что изменилось в объединенной версии

### ✅ Преимущества новой версии:
- **Одна команда** вместо двух: `docker-compose up -d`
- **Единая сеть** - решены все проблемы с networking
- **Именованные контейнеры** с префиксом `bionicpro-*`
- **Оптимизированные зависимости** - правильный порядок запуска
- **Упрощенная отладка** - все логи в одном месте
- **Централизованная конфигурация** - все в одном файле

### 📁 Файловые изменения:
- ✅ `docker-compose.yaml` - объединенный файл
- ✅ `unified-docker-compose-guide.md` - новое руководство
- ✅ `checks\test-services.bat` - скрипт тестирования
- 📦 `*.backup` - резервные копии старых файлов

### 🔄 Migration из старой версии:
Если у вас была запущена старая версия с двумя файлами:
```bash
# 1. Остановить старые сервисы
docker-compose down
docker-compose down

# 2. Запустить новую версию
docker-compose up -d

# 3. Проверить результат
checks\test-services.bat
```

### 🔧 Команды управления сервисами:
```bash
# Запуск всех сервисов
docker-compose up -d

# Запуск только UI части
docker-compose up -d keycloak_db keycloak frontend

# Запуск только аналитики
docker-compose up -d postgres-airflow redis clickhouse airflow-webserver airflow-scheduler

# Перезапуск конкретного сервиса
docker-compose restart keycloak

# Остановка всех сервисов
docker-compose down

# Остановка с удалением volumes (ОСТОРОЖНО!)
docker-compose down -v
```

**Время полного запуска**: 3-10 минут (улучшено благодаря оптимизации зависимостей)
**Система готова к production deployment**: ✅

---

**Версия**: 2.1.2 🆕
**Последнее обновление**: Февраль 2026
**Основные изменения**: Добавлены автоматические диагностические скрипты для Windows, переменные окружения для всех паролей БД
**Новые инструменты**: `checks\test-services.bat`, `checks\quick-health-check.bat`, `checks\health-check-full.bat`, `checks\troubleshoot-check.bat`
**Безопасность**: Все пароли БД вынесены в .env файл