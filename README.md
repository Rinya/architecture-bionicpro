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
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  ▲
       │                  │                  │
       ▼                  ▼                  │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Keycloak   │    │    Redis    │    │   Airflow   │
│   (Auth)    │    │   (Cache)   │    │    (ETL)    │
└─────────────┘    └─────────────┘    └─────────────┘
                                            ▲
                                            │
                                      ┌─────────────┐
                                      │    Kafka    │
                                      │ (Streaming) │
                                      └─────────────┘
```

## 🚀 Быстрый старт

### Предварительные требования
- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM
- 10GB+ свободного места

### Запуск системы
```bash
# Клонирование и переход в директорию
cd architecture-bionicpro

# Создание Docker сети
docker network create sprint9_default

# Запуск основных сервисов
docker-compose up -d

# Запуск ETL инфраструктуры
docker-compose -f docker-compose.airflow.yml up -d
```

**📚 Подробная инструкция**: См. [STARTUP_GUIDE.md](STARTUP_GUIDE.md)

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

## 📁 Структура проекта

```
architecture-bionicpro/
├── README.md                        # Этот файл
├── STARTUP_GUIDE.md                 # Подробная инструкция запуска
├── .env                            # Переменные окружения
├── docker-compose.yaml             # Основные сервисы
├── docker-compose.airflow.yml      # ETL инфраструктура
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
│   └── clickhouse-init.sql         # Инициализация ClickHouse
│
├── dags/                          # Airflow DAGs
├── logs/                          # Логи приложения
└── plugins/                       # Airflow плагины
```

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
# Проверка логов
docker-compose logs [service_name]

# Проверка состояния сервисов
docker-compose ps

# Тестирование API
curl -H "Authorization: Bearer $JWT_TOKEN" \
     "http://localhost:5000/reports/user1"
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

**Версия**: 1.0.0
**Последнее обновление**: Январь 2026
**Статус**: Production Ready ✅