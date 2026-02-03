# BionicPRO Reports System

## 📖 Описание

Система отчётов для протезов BionicPRO с интеграцией корпоративной аутентификации, OLAP-аналитики и ETL-процессами. Обеспечивает безопасный доступ пользователей к персональным данным телеметрии и аналитическим отчётам о работе протезов.

## 🏗️ Архитектура

### Основные компоненты:
- **Frontend**: React + TypeScript + Tailwind CSS
- **Backend**: Flask + JWT + Row-Level Security
- **Authentication**: Keycloak OIDC/SSO
- **OLAP Database**: ClickHouse
- **ETL**: Apache Airflow
- **Cache**: Redis
- **Message Streaming**: Apache Kafka

### Микросервисная архитектура:
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │────│   Backend   │────│ ClickHouse  │
│  (React)    │    │   (Flask)   │    │   (OLAP)    │
│    :3000    │    │    :5000    │    │ :8123,:9000 │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  ▲
       │                  │                  │
       ▼                  ▼                  │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Keycloak   │    │    Redis    │    │   Airflow   │
│   (Auth)    │    │   (Cache)   │    │    (ETL)    │
│    :8080    │    │    :6380    │    │    :8081    │
└─────────────┘    └─────────────┘    └─────────────┘
                                            ▲
                                            │
                                      ┌─────────────┐
                                      │    Kafka    │
                                      │ (Streaming) │
                                      │    :9092    │
                                      └─────────────┘
```

## 🚀 Быстрый старт

### Предварительные требования
- Docker 24.0+
- Docker Compose 2.20+
- 12GB+ RAM
- 15GB+ свободного места

### ⚡ Единая команда запуска (НОВОЕ!)
```bash
# Клонирование и переход в директорию
cd architecture-bionicpro

# Настройка окружения
cp .env.example .env
# ⚠️  ВАЖНО: Настройте переменные в .env файле (см. раздел "Настройка .env")

# Запуск ВСЕГО стека одной командой
docker-compose up -d
```

### 🎯 Что изменилось:
- ✅ **Объединены Docker Compose файлы** - теперь один файл вместо двух
- ✅ **Единая сеть** - решены все проблемы с networking
- ✅ **Упрощенный запуск** - одна команда для всех сервисов

**📚 Подробная инструкция**: См. [STARTUP_GUIDE.md](STARTUP_GUIDE.md)

### ⚠️  Настройка .env файла

**Обязательная конфигурация:**
```bash
# 1. Создать .env файл
cp .env.example .env

# 2. Настроить переменные (детали ниже)
nano .env
```

**Ключевые переменные для настройки:**

| Переменная | Описание | Как получить |
|------------|----------|--------------|
| `JWT_SECRET_KEY` | Секретный ключ для JWT токенов | Сгенерировать: `openssl rand -hex 32` или `python -c "import secrets; print(secrets.token_hex(32))"` |
| `BITRIX24_WEBHOOK_URL` | Webhook для интеграции с Bitrix24 | 1. Войти в Bitrix24 → Приложения → Webhook<br>2. Создать входящий webhook<br>3. Скопировать URL |
| `POSTGRES_PASSWORD` | Пароль для баз данных | Создать надежный пароль |
| `CLICKHOUSE_PASSWORD` | Пароль ClickHouse | Создать надежный пароль |
| `REDIS_PASSWORD` | Пароль Redis | Создать надежный пароль |

**Пример правильно настроенного .env:**
```bash
JWT_SECRET_KEY=a4f8b2c1d5e9f7a3b8c2d6e0f4a7b1c5d8e2f6a0b4c8d2e6f0a4b8c1d5e9f7a3
BITRIX24_WEBHOOK_URL=https://mycompany.bitrix24.com/rest/1/abc123xyz/
POSTGRES_PASSWORD=SecurePostgresPassword123!
CLICKHOUSE_PASSWORD=SecureClickhousePassword123!
REDIS_PASSWORD=SecureRedisPassword123!
```

**⚠️  ВАЖНО:**
- **НИКОГДА** не коммитьте `.env` файл в git!
- Используйте **разные пароли** для каждого сервиса
- Генерируйте **новый JWT_SECRET_KEY** для каждой установки

## 🔐 Безопасность

### Реализованные меры защиты:
- ✅ **OAuth 2.0 + OIDC** через Keycloak
- ✅ **JWT токены** с автоматическим обновлением
- ✅ **Row-Level Security** на уровне базы данных
- ✅ **Строгая авторизация** - пользователи видят только свои данные
- ✅ **Audit logging** всех операций доступа к данным
- ✅ **Rate limiting** для предотвращения злоупотреблений
- ✅ **HTTPS/TLS** готовность для production

### Валидация данных:
- Проверка принадлежности устройств пользователю
- Валидация временных периодов
- Проверка доступности обработанных данных

## 📊 Функциональность

### Для пользователей:
- 📈 **Персональные отчёты** по телеметрии протезов
- 📱 **Адаптивный интерфейс** для всех устройств
- 📋 **Экспорт отчётов** в JSON, PDF, Excel
- 🎯 **Детальная аналитика** с трендами и рекомендациями
- ⚡ **Быстрая загрузка** с кэшированием

### Административные возможности:
- 👥 **Управление пользователями** через Keycloak
- 📊 **ETL мониторинг** через Airflow UI
- 🔍 **Логи и аудит** доступа к данным
- 🚨 **Мониторинг системы** и алертинг

## 🌐 Endpoints

### Пользовательские API:
```http
GET /reports/{user_id}              # Основные отчёты
GET /reports/{user_id}/devices      # Список устройств
GET /reports/{user_id}/summary      # Сводка показателей
```

### Системные endpoints:
```http
GET /health                         # Health check
POST /auth/login                    # Аутентификация
GET /metrics                        # Prometheus метрики
```

## 🖥️ UI доступ

- **Пользовательский интерфейс**: http://localhost:3000
- **API Backend**: http://localhost:5000
- **Keycloak Admin**: http://localhost:8080/admin
- **Airflow UI**: http://localhost:8081
- **ClickHouse Play**: http://localhost:8123/play

### Порты сервисов:
- **Frontend (React)**: 3000
- **Backend API (Flask)**: 5000
- **Keycloak**: 8080
- **Keycloak DB (PostgreSQL)**: 5433
- **Airflow UI**: 8081
- **Airflow DB (PostgreSQL)**: 5434
- **ClickHouse**: 8123, 9000
- **Redis**: 6380
- **Kafka**: 9092

## 📁 Структура проекта

```
architecture-bionicpro/
├── README.md                        # Этот файл
├── STARTUP_GUIDE.md                 # Подробная инструкция запуска
├── unified-docker-compose-guide.md # Руководство по объединенной конфигурации
├── .env                            # Переменные окружения (не в git)
├── .env.example                    # Шаблон переменных окружения
├── docker-compose.yaml             # 🆕 ВСЕ СЕРВИСЫ (объединенный файл)
├── docker-compose.*.backup         # Резервные копии старых файлов
├── test-services.bat               # 🆕 Скрипт тестирования сервисов
│
├── frontend/                       # React UI
│   ├── src/components/             # UI компоненты
│   ├── public/                     # Статические файлы
│   └── package.json                # NPM зависимости
│
├── backend/                        # Flask API
│   ├── app.py                      # Главный файл приложения
│   ├── Dockerfile                  # Docker конфигурация
│   └── requirements.txt            # Python зависимости
│
├── keycloak/                       # Конфигурация Keycloak
│   └── realm-export.json           # Настройки realm
│
├── sql/                           # SQL скрипты
│   └── clickhouse-init.sql         # Инициализация ClickHouse (обновлен)
│
├── dags/                          # Airflow DAGs
├── logs/                          # Логи приложения
└── plugins/                       # Airflow плагины
```

### 🆕 **Что изменилось в файловой структуре:**
- **`docker-compose.yaml`** - объединенный файл со всеми сервисами
- **`unified-docker-compose-guide.md`** - документация по новой структуре
- **`test-services.bat`** - быстрый тест всех сервисов
- **`sql/clickhouse-init.sql`** - обновлен синтаксис для ClickHouse 23+

## 🔧 Разработка

### Локальная разработка Frontend:
```bash
cd frontend
npm install
npm start
```

### Локальная разработка Backend:
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Отладка и тестирование:
```bash
# Запуск всех сервисов
docker-compose up -d

# Быстрая проверка всех сервисов (Windows)
test-services.bat

# Проверка логов
docker-compose logs [service_name]

# Проверка состояния сервисов
docker-compose ps

# Тестирование отдельных сервисов
curl http://localhost:8080/realms/reports-realm  # Keycloak
curl http://localhost:8081/health               # Airflow
curl http://localhost:8123/ping                 # ClickHouse
curl http://localhost:3000                      # Frontend

# Тестирование API с токеном
curl -H "Authorization: Bearer $JWT_TOKEN" \
     "http://localhost:5000/reports/user1"

# Запуск только определенной группы сервисов
docker-compose up -d keycloak_db keycloak frontend  # Только UI
docker-compose up -d postgres-airflow redis airflow-webserver  # Только Airflow
```

## 📈 Мониторинг и производительность

### Метрики системы:
- Response time API endpoints
- Database query performance
- Cache hit ratio
- Authentication success rate
- ETL job completion status

### Логирование:
- Audit trail всех действий пользователей
- API access logs с JWT валидацией
- ETL job execution logs
- System health monitoring

## 🚢 Production Deployment

### Готовность к production:
- ✅ Все сервисы в Docker контейнерах
- ✅ Environment-based конфигурация
- ✅ Health checks для всех сервисов
- ✅ Horizontal scaling готовность
- ✅ HTTPS/TLS конфигурация
- ✅ Backup и recovery процедуры

### Масштабирование:
- Frontend: Nginx load balancer
- Backend: Multiple Flask instances
- Database: ClickHouse clustering
- Cache: Redis Cluster
- ETL: Airflow CeleryExecutor

## 🤝 Участие в разработке

### Требования:
- Соблюдение кодировочных стандартов
- Unit и integration тесты
- Документация изменений
- Security review для критических изменений

### Тестирование:
```bash
# Frontend тесты
cd frontend && npm test

# Backend тесты
cd backend && pytest

# E2E тесты
npm run test:e2e
```

## 📞 Поддержка и контакты

- **Техническая поддержка**: admin@bionicpro.com
- **Документация**: Обновляется при каждом релизе
- **Время ответа SLA**: 24 часа для критических issues

## 📄 Лицензия

Proprietary - BionicPRO Enterprise License

---

**Версия**: 2.0.0 🆕
**Последнее обновление**: Февраль 2026
**Статус**: Production Ready ✅
**Основные изменения**: Объединение Docker Compose файлов, единая команда запуска