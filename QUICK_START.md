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
checks\test-services.bat

# ИЛИ краткая диагностика с подсчетом результатов
checks\quick-health-check.bat
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

### Автоматическая диагностика (НОВОЕ!):
```bash
# Проверка проблем с автоматическими предложениями решений
checks\troubleshoot-check.bat

# Полная диагностика системы
checks\health-check-full.bat
```

### Ручная диагностика:
1. **Проверить порты:** Убедиться, что порты 3000, 5000, 8080, 8081 свободны
2. **Проверить ресурсы:** Минимум 8GB RAM доступно
3. **Логи ошибок:** `docker-compose logs [service-name]`
4. **Полная перезагрузка:** `docker-compose down && docker-compose up -d`

## 🛠️ Доступные диагностические инструменты:

| Скрипт | Назначение | Время выполнения |
|--------|------------|------------------|
| `checks\test-services.bat` | Быстрый тест endpoints | ~30 секунд |
| `checks\quick-health-check.bat` | Краткая диагностика + статистика | ~1 минута |
| `checks\health-check-full.bat` | Полная проверка системы | ~3 минуты |
| `checks\troubleshoot-check.bat` | Диагностика проблем + решения | ~2 минуты |

📚 **Подробная документация:** [STARTUP_GUIDE.md](STARTUP_GUIDE.md)

---

**Версия**: 2.1.0 🆕
**Обновлено**: Февраль 2026
**Новое**: Автоматические диагностические скрипты для быстрого устранения проблем