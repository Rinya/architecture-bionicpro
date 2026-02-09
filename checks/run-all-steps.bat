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
echo     BionicPRO Complete Setup Wizard
echo     Автоматическое выполнение всех шагов
echo ========================================
echo.

echo [INFO] This script will run all BionicPRO setup and testing steps:
echo.
echo Step 4: Data initialization
echo Step 5: Functionality testing
echo Step 6: UI testing
echo Step 7: Airflow testing
echo Step 8: Complete system check
echo Step 9: Final verification
echo.

set /p confirm="Do you want to proceed with all steps? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Setup cancelled by user.
    pause
    exit /b 0
)

echo.
echo Starting complete BionicPRO setup and testing...
echo.

echo ========================================
echo        STEP 4: Data Initialization
echo ========================================
echo.

call checks\init-test-data.bat
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Step 4 failed. Stopping execution.
    pause
    exit /b 1
)

echo.
echo Press any key to continue to Step 5...
pause > nul

echo ========================================
echo      STEP 5: Functionality Testing
echo ========================================
echo.

call checks\step5-functionality-test.bat
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Step 5 failed. Stopping execution.
    pause
    exit /b 1
)

echo.
echo Press any key to continue to Step 6...
pause > nul

echo ========================================
echo          STEP 6: UI Testing
echo ========================================
echo.

call checks\step6-ui-test.bat
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Step 6 failed. Stopping execution.
    pause
    exit /b 1
)

echo.
echo Press any key to continue to Step 7...
pause > nul

echo ========================================
echo        STEP 7: Airflow Testing
echo ========================================
echo.

call checks\step7-airflow-test.bat
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Step 7 failed. Stopping execution.
    pause
    exit /b 1
)

echo.
echo Press any key to continue to Step 8...
pause > nul

echo ========================================
echo      STEP 8: Complete System Check
echo ========================================
echo.

call checks\step8-complete-check.bat
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Step 8 failed. Stopping execution.
    pause
    exit /b 1
)

echo.
echo Press any key to continue to Final Verification...
pause > nul

echo ========================================
echo      STEP 9: Final Verification
echo ========================================
echo.

call checks\step9-final-verification.bat
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Step 9 failed. Please review results.
    pause
    exit /b 1
)

echo.
echo ========================================
echo       COMPLETE SETUP FINISHED!
echo ========================================
echo.

echo [🎉] Congratulations! All BionicPRO setup steps completed.
echo.
echo What was accomplished:
echo ✅ Test data initialized in ClickHouse
echo ✅ API functionality verified
echo ✅ UI components tested
echo ✅ Airflow ETL pipeline prepared
echo ✅ Complete system health checked
echo ✅ Production readiness verified
echo.
echo Your BionicPRO system is ready for use!
echo.
echo Quick access:
echo → Frontend: http://localhost:3000
echo → Admin:    http://localhost:8080/admin
echo.
echo Need help? Check:
echo → STARTUP_GUIDE.md for detailed instructions
echo → troubleshoot-check.bat for problem diagnosis
echo.
echo Press any key to exit...
pause > nul