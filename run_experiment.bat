@echo off
REM FaultLab experiment runner for Windows

echo 🧪 FaultLab Chaos Engineering Experiment
echo ========================================
echo.

REM Check if services are running
docker-compose ps | findstr "Up" >nul
if %errorlevel% neq 0 (
    echo ⚠️  Services not running. Starting...
    docker-compose up -d
    timeout /t 10 /nobreak >nul
)

echo ✓ Services are running
echo.

REM Baseline traffic
echo 📊 Phase 1: Baseline (no faults)
echo Generating 10 orders...
for /L %%i in (1,1,10) do (
    curl -s -X POST http://localhost:3000/orders -H "Content-Type: application/json" -d "{\"customer_id\": \"CUST-%%i\", \"amount\": 99.99}" >nul
    echo | set /p=.
)
echo  Done!
timeout /t 2 /nobreak >nul

REM Get scenario from argument or default
set SCENARIO=%1
if "%SCENARIO%"=="" set SCENARIO=latency

set DURATION=%2
if "%DURATION%"=="" set DURATION=30

echo.
echo 🔥 Phase 2: Chaos Injection
echo Scenario: %SCENARIO%
echo Duration: %DURATION%s
echo.

REM Run scenario
start /b docker exec faultlab-api-gateway-1 python chaos/scenarios.py %SCENARIO% %DURATION%

timeout /t 5 /nobreak >nul

REM Traffic under chaos
echo Generating traffic under chaos...
for /L %%i in (11,1,20) do (
    curl -s -X POST http://localhost:3000/orders -H "Content-Type: application/json" -d "{\"customer_id\": \"CUST-%%i\", \"amount\": 149.99}" >nul
    echo | set /p=.
    timeout /t 1 /nobreak >nul
)
echo  Done!

timeout /t %DURATION% /nobreak >nul

echo.
echo 🔍 Phase 3: Analysis
echo.

REM Run diagnostics
python verification\runbook.py

echo.
echo 📈 View detailed traces at: http://localhost:16686
echo.
echo ✅ Experiment complete!
