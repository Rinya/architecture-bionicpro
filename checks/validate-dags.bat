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
echo     BionicPRO DAG Validation
echo     Проверка синтаксиса DAG файлов
echo ========================================
echo.

echo [INFO] Запуск проверки DAG файлов...
echo.

python checks\validate-dags.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Валидация прошла успешно!
    echo   Все DAG файлы готовы для использования в Airflow.
) else (
    echo.
    echo ❌ Найдены ошибки в DAG файлах!
    echo   Исправьте ошибки перед запуском Airflow.
)

echo.
echo Press any key to exit...
pause > nul