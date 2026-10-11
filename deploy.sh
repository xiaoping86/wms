#!/usr/bin/env bash
# 库管易仓库管理系统 — Linux / macOS 一键部署脚本
set -euo pipefail
cd "$(dirname "$0")"

PORT=8088
CONTAINER=kuguanyi-wms

echo "============================================================"
echo "      库管易仓库管理系统  一键部署"
echo "============================================================"

# 1. 检查 Docker
if ! command -v docker >/dev/null 2>&1; then
  echo "[错误] 未检测到 docker，请先安装 Docker Desktop / Docker Engine。"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "[错误] Docker 未运行，请启动 Docker 后重试。"
  exit 1
fi

# 2. 端口检测
if command -v ss >/dev/null 2>&1; then
  if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
    echo "[警告] 端口 ${PORT} 已被占用，请编辑 docker-compose.yml 修改端口映射后重试。"
    exit 1
  fi
elif command -v lsof >/dev/null 2>&1; then
  if lsof -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[警告] 端口 ${PORT} 已被占用，请编辑 docker-compose.yml 修改端口映射后重试。"
    exit 1
  fi
fi

# 3. 构建并启动
echo "[1/3] 正在构建镜像（首次较慢，需下载依赖）..."
docker compose up -d --build

# 4. 等待健康检查
echo "[2/3] 正在等待服务启动..."
for i in $(seq 1 40); do
  st=$(docker inspect -f '{{.State.Health.Status}}' "${CONTAINER}" 2>/dev/null || true)
  if [ "$st" = "healthy" ]; then break; fi
  sleep 2
done

# 5. 提示访问地址
LANIP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
echo "[3/3] 部署完成！"
echo "  本机访问：   http://localhost:${PORT}"
[ -n "$LANIP" ] && echo "  局域网访问： http://${LANIP}:${PORT}"
echo "  默认账号：   admin / admin123"
echo ""
echo "  查看日志： docker logs -f ${CONTAINER}"
echo "  停止服务： docker compose down"
echo ""

# 尝试自动打开浏览器
if command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:${PORT}" >/dev/null 2>&1 || true; fi
if command -v open >/dev/null 2>&1; then open "http://localhost:${PORT}" >/dev/null 2>&1 || true; fi
