# ⚡ BionicPRO - Быстрый старт (5 минут)

## 🚀 Один файл, одна команда!

### Шаг 1: Настройка окружения
```bash
# Клонировать проект
git clone <repository-url>
cd architecture-bionicpro

# Создать .env файл
cp .env.example .env
```

### Шаг 2: Настроить .env файл
Отредактируйте `.env` и замените:

```bash
# ОБЯЗАТЕЛЬНО сгенерировать новый JWT ключ
openssl rand -hex 32

# Придумать надежные пароли для БД
# Получить Bitrix24 webhook URL (или использовать тестовую заглушку)
```

### Шаг 3: Запуск
```bash
# ЕДИНСТВЕННАЯ команда для запуска ВСЕХ сервисов!
docker-compose up -d

# Дождаться готовности (3-5 минут)
docker-compose ps

# Автотест всех сервисов (Windows)
test-services.bat
```

## 🌐 Готово! Доступные URL:

| Сервис | URL | Логин/Пароль |
|--------|-----|--------------|
| **Frontend** | http://localhost:3000 | - |
| **Keycloak** | http://localhost:8080/admin/ | admin/admin |
| **Airflow** | http://localhost:8081 | admin/admin |
| **ClickHouse** | http://localhost:8123/play | bionicpro_user |
| **Reports API** | http://localhost:5000/health | - |

## 🔧 Быстрые команды:

```bash
# Перезапуск всех сервисов
docker-compose restart

# Остановка всех сервисов
docker-compose down

# Логи конкретного сервиса
docker-compose logs keycloak

# Статус всех сервисов
docker-compose ps
```

## 🆘 Если что-то не работает:

1. **Проверить порты:** Убедиться, что порты 3000, 5000, 8080, 8081 свободны
2. **Проверить ресурсы:** Минимум 8GB RAM доступно
3. **Логи ошибок:** `docker-compose logs [service-name]`
4. **Полная перезагрузка:** `docker-compose down && docker-compose up -d`

📚 **Подробная документация:** [STARTUP_GUIDE.md](STARTUP_GUIDE.md)