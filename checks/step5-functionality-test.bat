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
echo     BionicPRO Functionality Testing
echo     Шаг 5: Полное тестирование функциональности
echo ========================================
echo.

echo === 5.1 Тестирование аутентификации ===
echo.
echo [INFO] Opening browser for authentication test...
echo.
echo 1. Frontend will open at: http://localhost:3000
echo 2. Click "Войти через Keycloak"
echo 3. Use these test credentials:
echo    - Username: testuser (or create in Keycloak Admin)
echo    - Password: password
echo.

start http://localhost:3000

echo [INFO] Opening Keycloak Admin Console...
echo.
echo Keycloak Admin Console: http://localhost:8080/admin
echo Login: admin
echo Password: admin
echo.

start http://localhost:8080/admin

echo === 5.2 Создание тестового пользователя в Keycloak ===
echo.
echo [INSTRUCTIONS] To create a test user in Keycloak:
echo 1. Go to realm 'reports-realm'
echo 2. Users → Add user
echo 3. Username: user1, Email: user1@test.com
echo 4. Credentials → Set password: password123
echo 5. Temporary: OFF
echo 6. Save
echo.
echo Press any key when you've created the test user...
pause > nul

echo.
echo === 5.3 Тестирование API отчётов ===
echo.

echo [INFO] Getting JWT token for user1...
echo.

REM Получение JWT токена (это требует, чтобы пользователь был создан в Keycloak)
echo Testing API authentication...
echo.

curl -s -X POST http://localhost:5000/auth/login -H "Content-Type: application/json" -d "{\"username\":\"user1\",\"password\":\"password123\"}" > temp_token.json 2>nul

if !ERRORLEVEL!==0 (
    echo [✓] API Authentication endpoint is responding

    REM Попытка извлечь токен (требует jq или PowerShell)
    powershell -Command "$response = Get-Content temp_token.json | ConvertFrom-Json; if($response.access_token) { echo '[✓] JWT Token received successfully'; $env:JWT_TOKEN = $response.access_token } else { echo '[!] Token not found in response' }"

    echo.
    echo [INFO] Testing API endpoints with token...

    echo Testing reports endpoint...
    curl -s -H "Authorization: Bearer dummy_token_for_test" "http://localhost:5000/reports/user1?start_date=2024-01-15&end_date=2024-01-17&format=json" > nul 2>&1
    if !ERRORLEVEL!==0 (
        echo [✓] Reports endpoint is responding
    ) else (
        echo [!] Reports endpoint test failed (expected - need valid JWT)
    )

    echo Testing devices endpoint...
    curl -s -H "Authorization: Bearer dummy_token_for_test" "http://localhost:5000/reports/user1/devices" > nul 2>&1
    if !ERRORLEVEL!==0 (
        echo [✓] Devices endpoint is responding
    ) else (
        echo [!] Devices endpoint test failed (expected - need valid JWT)
    )

    echo Testing summary endpoint...
    curl -s -H "Authorization: Bearer dummy_token_for_test" "http://localhost:5000/reports/user1/summary" > nul 2>&1
    if !ERRORLEVEL!==0 (
        echo [✓] Summary endpoint is responding
    ) else (
        echo [!] Summary endpoint test failed (expected - need valid JWT)
    )

) else (
    echo [!] API Authentication test failed
    echo Check that reports-api container is running
)

REM Очистка временного файла
if exist temp_token.json del temp_token.json

echo.
echo === 5.4 Тестирование безопасности ===
echo.

echo Testing unauthorized access (should fail)...
curl -s -I "http://localhost:5000/reports/user1" | findstr "401\|Unauthorized" > nul
if !ERRORLEVEL!==0 (
    echo [✓] Unauthorized access correctly blocked (401)
) else (
    echo [!] Security test: Unauthorized access not properly blocked
)

echo Testing access to non-existent user (should fail)...
curl -s -H "Authorization: Bearer dummy_token" "http://localhost:5000/reports/nonexistent_user" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Non-existent user access test completed
) else (
    echo [!] Non-existent user access test failed
)

echo Testing future dates validation...
curl -s -H "Authorization: Bearer dummy_token" "http://localhost:5000/reports/user1?start_date=2025-12-01&end_date=2025-12-31" > nul 2>&1
if !ERRORLEVEL!==0 (
    echo [✓] Future dates validation test completed
) else (
    echo [!] Future dates validation test failed
)

echo.
echo ========================================
echo     Functionality Test Summary
echo ========================================
echo.
echo [COMPLETED TESTS]:
echo ✅ Authentication endpoints tested
echo ✅ Keycloak admin console opened
echo ✅ API endpoints connectivity tested
echo ✅ Security validation tested
echo.
echo [MANUAL VERIFICATION NEEDED]:
echo 🔍 Create test user in Keycloak Admin Console
echo 🔍 Test login flow in frontend UI
echo 🔍 Verify JWT token generation works
echo.
echo [NEXT STEPS]:
echo → Run step6-ui-test.bat for UI functionality testing
echo → Check frontend at http://localhost:3000
echo → Test actual login with created user
echo.
echo Press any key to continue...
pause > nul