@echo off
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
echo     BionicPRO UI Functionality Testing
echo     Шаг 6: Тестирование UI функциональности
echo ========================================
echo.

echo === 6.1 Обзор UI компонентов ===
echo.
echo [INFO] UI Components Overview:
echo ✓ ReportPage (frontend/src/components/ReportPage.tsx) - основная страница отчётов
echo ✓ UserSummary (frontend/src/components/UserSummary.tsx) - сводка пользователя за 30 дней
echo ✓ ReportPreview (frontend/src/components/ReportPreview.tsx) - детальное отображение отчётов
echo.

echo [INFO] UI Functionality Features:
echo ✓ Аутентификация через Keycloak с автоматическим обновлением JWT токенов
echo ✓ Строгий контроль доступа - пользователи видят только свои данные
echo ✓ Выбор периода и фильтрация по устройствам
echo ✓ Экспорт в разных форматах (JSON, PDF, Excel)
echo ✓ Адаптивный дизайн для мобильных устройств
echo ✓ Цветовые индикаторы состояния и тренды показателей
echo.

echo === 6.2 Браузерное тестирование ===
echo.

echo [INFO] Opening frontend for browser testing...
start http://localhost:3000

echo.
echo [TESTING CHECKLIST] Please perform these tests manually:
echo.
echo □ 1. Frontend loads at http://localhost:3000
echo □ 2. Login with user1 through Keycloak
echo □ 3. User summary loads automatically:
echo   □ Активные дни
echo   □ Общее время использования
echo   □ Эффективность движений
echo   □ Здоровье батареи
echo   □ Техническое состояние
echo   □ Количество аномалий
echo.
echo □ 4. Change date period to 2024-01-15 → 2024-01-17
echo □ 5. Select device or leave "Все устройства"
echo □ 6. Test report format selection:
echo   □ JSON - для просмотра в браузере
echo   □ PDF - для печати и архивирования
echo   □ Excel - для дальнейшего анализа
echo.
echo □ 7. Click "Показать отчёт" or "Скачать отчёт"
echo □ 8. Verify data display:
echo   □ Summary indicators with color codes
echo   □ Trends (📈 улучшается, 📉 ухудшается, 📊 стабильно)
echo   □ Improvement recommendations
echo   □ Detailed daily data table
echo.

echo === 6.3 Цветовые коды состояния ===
echo.
echo Color Status Indicators:
echo 🟢 Green (80-100%%): Отличное состояние
echo 🟡 Yellow (60-79%%): Нормальное состояние
echo 🔴 Red (0-59%%): Требует внимания
echo.

echo === 6.4 Проверка валидации данных ===
echo.
echo [VALIDATION TEST]:
echo 1. Select future dates (tomorrow - day after tomorrow)
echo 2. Click "Показать отчёт"
echo 3. Should show: "Данные за будущие даты недоступны"
echo.

echo Press any key when you've completed browser testing...
pause > nul

echo.
echo === 6.5 Проверка безопасности в UI ===
echo.
echo [SECURITY CHECK INSTRUCTIONS]:
echo 1. Open Developer Tools → Network tab
echo 2. Generate a report
echo 3. Verify request has:
echo   □ Authorization header present
echo   □ URL contains correct user_id
echo   □ Parameters passed correctly
echo.

echo === 6.6 Проверка обработки ошибок ===
echo.
echo [ERROR HANDLING] UI should correctly handle:
echo ✓ 401 Unauthorized - automatic redirect to login
echo ✓ 403 Forbidden - "Доступ запрещён" message
echo ✓ 429 Rate Limited - "Превышен лимит запросов"
echo ✓ 500 Server Error - "Внутренняя ошибка сервера"
echo ✓ Network errors - "Ошибка подключения к серверу"
echo.

echo === 6.7 Мобильная версия ===
echo.
echo [MOBILE TEST INSTRUCTIONS]:
echo 1. Switch Developer Tools to mobile view
echo 2. Verify all elements are accessible and user-friendly
echo 3. Check touch-friendly interface (buttons minimum 44px)
echo.

echo === 6.8 API Endpoints для UI ===
echo.
echo Testing UI API endpoints connectivity...

echo Testing API health endpoint...
curl -s http://localhost:5000/health | findstr "healthy" > nul
if !ERRORLEVEL!==0 (
    echo [✓] API health check - responding
) else (
    echo [✗] API health check - failed
)

echo Testing frontend accessibility...
curl -s -I http://localhost:3000 | findstr "200" > nul
if !ERRORLEVEL!==0 (
    echo [✓] Frontend - responding
) else (
    echo [✗] Frontend - failed
)

echo.
echo ========================================
echo     UI Testing Summary
echo ========================================
echo.
echo [AUTOMATED TESTS COMPLETED]:
echo ✅ UI components overview provided
echo ✅ Browser opened for manual testing
echo ✅ API endpoints connectivity tested
echo ✅ Testing checklists provided
echo.
echo [MANUAL VERIFICATION REQUIRED]:
echo 🔍 Complete browser testing checklist above
echo 🔍 Verify authentication flow works
echo 🔍 Test report generation and display
echo 🔍 Check mobile responsiveness
echo 🔍 Validate error handling
echo.
echo [NEXT STEPS]:
echo → Run step7-airflow-test.bat for Airflow DAG testing
echo → Complete any failed manual tests
echo → Document any UI issues found
echo.
echo Press any key to continue...
pause > nul