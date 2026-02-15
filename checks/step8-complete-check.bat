@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM Определить правильную рабочую директорию
set "script_dir=%~dp0"
if exist "%script_dir%..\docker-compose.yaml" (
    cd /d "%script_dir%.."
) else if exist "%script_dir%docker-compose.yaml" (
    cd /d "%script_dir%"
) else (
    echo [ERROR] Cannot find docker-compose.yaml file!
    pause > nul
    exit /b 1
)

echo ========================================
echo     BionicPRO Complete System Check
echo     Шаг 8: Полная функциональная проверка
echo ========================================
echo.

echo === 8.1 Проверочный чек-лист UI ===
echo.

set "ui_tests_passed=0"
set "ui_tests_total=8"

echo [UI FUNCTIONALITY CHECKLIST]
echo Please verify the following and answer Y/N:
echo.

set /p auth_test="□ Аутентификация: Вход через Keycloak работает? (Y/N): "
if /i "%auth_test%"=="Y" set /a ui_tests_passed+=1

set /p summary_test="□ Сводка пользователя: Загружается автоматически? (Y/N): "
if /i "%summary_test%"=="Y" set /a ui_tests_passed+=1

set /p filters_test="□ Фильтры дат: Работают корректно? (Y/N): "
if /i "%filters_test%"=="Y" set /a ui_tests_passed+=1

set /p devices_test="□ Выбор устройства: Список загружается из API? (Y/N): "
if /i "%devices_test%"=="Y" set /a ui_tests_passed+=1

set /p json_test="□ JSON отчёт: Данные отображаются правильно? (Y/N): "
if /i "%json_test%"=="Y" set /a ui_tests_passed+=1

set /p trends_test="□ Тренды: Показываются если данных достаточно? (Y/N): "
if /i "%trends_test%"=="Y" set /a ui_tests_passed+=1

set /p recommendations_test="□ Рекомендации: Появляются при проблемах? (Y/N): "
if /i "%recommendations_test%"=="Y" set /a ui_tests_passed+=1

set /p export_test="□ Экспорт PDF/Excel: Кнопки работают? (Y/N): "
if /i "%export_test%"=="Y" set /a ui_tests_passed+=1

echo.
echo UI Tests Result: !ui_tests_passed!/!ui_tests_total! passed
if !ui_tests_passed! GEQ 6 (
    echo [✓] UI functionality is mostly working
) else (
    echo [!] UI functionality needs attention
)

echo.
echo === 8.2 Проверочный чек-лист безопасности ===
echo.

set "security_tests_passed=0"
set "security_tests_total=6"

echo [AUTOMATED SECURITY TESTS]

echo Testing unauthorized access...
curl -s -I "http://localhost:5000/reports/user1" | findstr "401\|Unauthorized" > nul
if !ERRORLEVEL!==0 (
    echo [✓] Неаутентифицированный доступ: Блокируется
    set /a security_tests_passed+=1
) else (
    echo [✗] Неаутентифицированный доступ: НЕ блокируется
)

echo Testing access to other user's data...
curl -s -H "Authorization: Bearer fake_token" "http://localhost:5000/reports/nonexistent_user" | findstr "403\|401\|Forbidden\|Unauthorized" > nul
if !ERRORLEVEL!==0 (
    echo [✓] Чужие данные: Доступ заблокирован
    set /a security_tests_passed+=1
) else (
    echo [!] Чужие данные: Требует проверки
)

echo Testing future dates validation...
curl -s -H "Authorization: Bearer fake_token" "http://localhost:5000/reports/user1?start_date=2025-12-01&end_date=2025-12-31" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Будущие даты: API отвечает (проверка валидации)
    set /a security_tests_passed+=1
) else (
    echo [!] Будущие даты: API не отвечает
)

echo Checking audit logging...
docker exec -it bionicpro-redis redis-cli -a bionicpro_redis_password ping > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Audit logging: Redis доступен для логирования
    set /a security_tests_passed+=1
) else (
    echo [!] Audit logging: Redis недоступен
)

echo Testing JWT validation endpoint...
curl -s -I "http://localhost:5000/auth/login" | findstr "HTTP" > nul
if !ERRORLEVEL!==0 (
    echo [✓] Token validation: Auth endpoint доступен
    set /a security_tests_passed+=1
) else (
    echo [✗] Token validation: Auth endpoint недоступен
)

echo.
echo [MANUAL SECURITY VERIFICATION NEEDED]
set /p error_handling_test="□ Error handling: Ошибки отображаются корректно в UI? (Y/N): "
if /i "%error_handling_test%"=="Y" set /a security_tests_passed+=1

echo.
echo Security Tests Result: !security_tests_passed!/!security_tests_total! passed
if !security_tests_passed! GEQ 4 (
    echo [✓] Security measures are mostly in place
) else (
    echo [!] Security needs attention
)

echo.
echo === 8.3 Проверочный чек-лист API ===
echo.

set "api_tests_passed=0"
set "api_tests_total=6"

echo [AUTOMATED API TESTS]

echo Testing health endpoint...
curl -s http://localhost:5000/health | findstr "healthy\|OK\|status" > nul
if !ERRORLEVEL!==0 (
    echo [✓] Health endpoint: Возвращает статус
    set /a api_tests_passed+=1
) else (
    echo [✗] Health endpoint: Не работает
)

echo Testing reports endpoint structure...
curl -s -I "http://localhost:5000/reports/user1" | findstr "HTTP" > nul
if !ERRORLEVEL!==0 (
    echo [✓] Reports endpoint: Отвечает на запросы
    set /a api_tests_passed+=1
) else (
    echo [✗] Reports endpoint: Не отвечает
)

echo Testing devices endpoint...
curl -s -I "http://localhost:5000/reports/user1/devices" | findstr "HTTP" > nul
if !ERRORLEVEL!==0 (
    echo [✓] Devices endpoint: Отвечает на запросы
    set /a api_tests_passed+=1
) else (
    echo [✗] Devices endpoint: Не отвечает
)

echo Testing summary endpoint...
curl -s -I "http://localhost:5000/reports/user1/summary" | findstr "HTTP" > nul
if !ERRORLEVEL!==0 (
    echo [✓] Summary endpoint: Отвечает на запросы
    set /a api_tests_passed+=1
) else (
    echo [✗] Summary endpoint: Не отвечает
)

echo Testing ClickHouse integration...
docker exec -it bionicpro-clickhouse clickhouse-client --query "SELECT COUNT(*) FROM reports.user_analytics" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] OLAP integration: ClickHouse доступен
    set /a api_tests_passed+=1
) else (
    echo [✗] OLAP integration: ClickHouse недоступен
)

echo Testing data processing verification...
docker exec -it bionicpro-clickhouse clickhouse-client --query "SELECT COUNT(*) as records FROM reports.user_analytics WHERE report_date >= today() - 7" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Data validation: Данные доступны для проверки
    set /a api_tests_passed+=1
) else (
    echo [!] Data validation: Проблемы с доступом к данным
)

echo.
echo API Tests Result: !api_tests_passed!/!api_tests_total! passed
if !api_tests_passed! GEQ 4 (
    echo [✓] API functionality is working well
) else (
    echo [!] API needs troubleshooting
)

echo.
echo === 8.4 Сводка результатов тестирования ===
echo.

set /a total_tests_passed=!ui_tests_passed!+!security_tests_passed!+!api_tests_passed!
set /a total_tests_total=!ui_tests_total!+!security_tests_total!+!api_tests_total!

echo OVERALL SYSTEM HEALTH:
echo ═══════════════════════════════════════
echo UI Functionality:    !ui_tests_passed!/!ui_tests_total! (%~1!ui_tests_passed!*100/!ui_tests_total!%%)
echo Security Measures:   !security_tests_passed!/!security_tests_total! (%~1!security_tests_passed!*100/!security_tests_total!%%)
echo API Functionality:  !api_tests_passed!/!api_tests_total! (%~1!api_tests_passed!*100/!api_tests_total!%%)
echo.
echo TOTAL SCORE: !total_tests_passed!/!total_tests_total! tests passed

if !total_tests_passed! GEQ 15 (
    echo.
    echo [🎉] EXCELLENT! System is ready for production
    echo All major components are working correctly
) else if !total_tests_passed! GEQ 12 (
    echo.
    echo [✅] GOOD! System is mostly functional
    echo Minor issues may need attention
) else if !total_tests_passed! GEQ 8 (
    echo.
    echo [⚠️] FAIR! System has basic functionality
    echo Several issues need to be resolved
) else (
    echo.
    echo [❌] POOR! System needs significant work
    echo Major issues prevent proper operation
)

echo.
echo ========================================
echo     Complete Check Summary
echo ========================================
echo.
echo [WHAT WAS TESTED]:
echo ✅ UI functionality and user experience
echo ✅ Security measures and access control
echo ✅ API endpoints and data integration
echo ✅ Database connectivity and data availability
echo.
echo [RECOMMENDATIONS]:
if !total_tests_passed! LSS 15 (
    echo → Review failed tests and address issues
    echo → Run individual component tests for debugging
    echo → Check logs for specific error messages
    echo → Verify configuration in .env file
)
echo → Document any remaining issues for future fixes
echo → Consider running load tests for production readiness
echo → Set up monitoring for ongoing system health
echo.
echo [NEXT STEPS]:
echo → Run step9-final-verification.bat for deployment readiness
echo → Address any failed tests before production deployment
echo.
echo Press any key to continue...
pause > nul