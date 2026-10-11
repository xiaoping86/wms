@echo off
setlocal enabledelayedexpansion
title 库管易仓库管理系统 - 一键部署
cd /d "%~dp0"

echo ============================================================
echo           库管易仓库管理系统  一键部署
echo ============================================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Docker，请先安装并启动 Docker Desktop。
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未运行，请先启动 Docker Desktop 后重试。
    pause
    exit /b 1
)

set PORT=8089
set PORT_BUSY=0
for /f "tokens=*" %%i in ('netstat -ano 2^>nul ^| findstr ":%PORT% "') do set PORT_BUSY=1

if "%PORT_BUSY%"=="1" (
    echo [错误] 端口 %PORT% 已被占用，无法绑定。
    echo.
    echo 解决办法：用记事本编辑 docker-compose.yml，把 "8089:8088"
    echo 改为其他空闲端口（如 "8090:8088"），保存后重跑本脚本。
    echo.
    echo 当前占用情况：
    netstat -ano | findstr ":%PORT% "
    pause
    exit /b 1
)

echo [1/3] 正在构建镜像并启动容器（首次约 3-5 分钟，请耐心等待）...
docker compose up -d --build
if errorlevel 1 (
    echo [错误] 部署失败，请查看上方日志。
    pause
    exit /b 1
)

echo [2/3] 正在等待服务就绪...
set /a tries=0
:wait
set /a tries+=1
for /f "tokens=*" %%s in ('docker inspect -f "{{.State.Health.Status}}" kuguanyi-wms 2^>nul') do set HEALTH=%%s
if "!HEALTH!"=="healthy" goto healthy
if !tries! geq 60 (
    echo [提示] 服务未按时就绪，请查看日志： docker logs kuguanyi-wms
    goto done
)
timeout /t 2 /nobreak >nul
goto wait

:healthy
echo [3/3] 服务已就绪！

:done
set "LANIP="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set "LANIP=%%a"
if defined LANIP set "LANIP=!LANIP: =!"

echo.
echo ============================================================
echo   部署完成！
echo     本机访问：   http://localhost:8089
if defined LANIP echo     局域网访问： http://!LANIP!:8089
echo     默认账号：   admin / admin123
echo ============================================================
echo.
echo 常用命令：
echo   查看日志： docker logs -f kuguanyi-wms
echo   停止服务： docker compose down
echo.
start "" "http://localhost:8089"
pause
