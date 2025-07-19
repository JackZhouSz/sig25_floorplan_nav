@echo off
REM run_routes.bat - 執行路徑預運算和視覺化腳本 (共用輸出目錄版本)

REM 使用說明:
REM   此腳本用於自動化執行 Path-finding 專案的路徑預運算和視覺化。
REM   你可以透過命令列參數指定各種選項。

REM 參數:
REM   %1: 起點 Cell ID (必填)
REM   %2: 共用輸出目錄 (選填，預設為 routes_and_viz)
REM   %3: 是否允許斜向移動 (選填，true 或 false，預設為 false)
REM   %4: 轉彎額外成本 (選填，浮點數，預設為 0.0)
REM   %5: 是否允許進入大區域 (選填，true 或 false，預設為 false)

REM 範例:
REM   預運算起點 1 到所有 booth，並視覺化，使用預設共用目錄和參數:
REM     run_routes.bat 1

REM   預運算起點 52，輸出到 my_output 目錄，允許斜向移動:
REM     run_routes.bat 52 my_output true

REM   預運算起點 1，加入 0.5 的轉彎成本:
REM     run_routes.bat 1 default_output false 0.5

REM --- 設定預設值 ---
set "START_IDX=%~1"
set "SHARED_OUTPUT_DIR=%~2"
if "%SHARED_OUTPUT_DIR%"=="" set "SHARED_OUTPUT_DIR=routes_and_viz"

set "ALLOW_DIAG=false"
if /i "%~3"=="true" set "ALLOW_DIAG=--allow-diag"
if /i "%~3"=="false" set "ALLOW_DIAG="

set "TURN_WEIGHT_ARG="
if not "%~4"=="" set "TURN_WEIGHT_ARG=--turn-weight %~4"

set "ALLOW_ENTER_AREA="
if /i "%~5"=="true" set "ALLOW_ENTER_AREA=--allow-enter-area"
if /i "%~5"=="false" set "ALLOW_ENTER_AREA="

REM --- 檢查必要參數 ---
if "%START_IDX%"=="" (
    echo.
    echo 錯誤: 請提供起點 Cell ID。
    echo 範例: run_routes.bat 1
    echo.
    goto :eof
)

echo.
echo === 準備執行路徑處理 ===
echo 起點 Cell ID: %START_IDX%
echo 共用輸出目錄: %SHARED_OUTPUT_DIR%
echo 允許斜向移動: %ALLOW_DIAG%
echo 轉彎成本: %TURN_WEIGHT_ARG%
echo 允許進入大區域: %ALLOW_ENTER_AREA%
echo.

REM --- 執行路徑預運算 ---
echo.
echo --- 步驟 1/2: 執行路徑預運算 ---
python scripts/precompute_routes.py %START_IDX% --output-dir %SHARED_OUTPUT_DIR% %ALLOW_DIAG% %TURN_WEIGHT_ARG% %ALLOW_ENTER_AREA%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 錯誤: 路徑預運算失敗。
    goto :eof
)

REM --- 執行路徑視覺化 ---
echo.
echo --- 步驟 2/2: 執行路徑視覺化 ---
set "PRECOMPUTED_ROUTE_FILE=%SHARED_OUTPUT_DIR%/%START_IDX%_to_all.json"
python scripts/batch_visualize.py %PRECOMPUTED_ROUTE_FILE% --output-dir %SHARED_OUTPUT_DIR%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 錯誤: 路徑視覺化失敗。
    goto :eof
)

echo.
echo --- 所有步驟已完成 ---
echo. 