#!/bin/sh
# 库管易仓储系统 启动脚本
# 1) 确保存在本地自签证书（持久化到 /data/certs，重建不丢）
# 2) 同时提供 HTTP(8088) 与 HTTPS(8443) 两个访问入口
#    HTTPS 入口让浏览器把页面判定为"安全上下文"，从而允许网页弹出
#    系统"另存为"窗口，把备份真正保存到电脑任意文件夹。

set -e

CERT_DIR=/data/certs
CRT=$CERT_DIR/server.crt
KEY=$CERT_DIR/server.key

mkdir -p "$CERT_DIR"

if [ ! -s "$CRT" ] || [ ! -s "$KEY" ]; then
  echo "[start] 生成本地自签证书 ..."
  CONTAINER_IP=$(hostname -i 2>/dev/null | awk '{print $1}')
  SAN="DNS:localhost,DNS:kuguanyi,DNS:kuguanyi.local,IP:127.0.0.1,IP:::1"
  if [ -n "$CONTAINER_IP" ]; then SAN="$SAN,IP:$CONTAINER_IP"; fi
  if [ -n "$WMS_LAN_IP" ]; then SAN="$SAN,IP:$WMS_LAN_IP"; fi
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY" -out "$CRT" -days 3650 \
    -subj "/CN=KuGuanYi WMS" \
    -addext "subjectAltName=$SAN" \
    -addext "basicConstraints=CA:TRUE" \
    -addext "keyUsage=digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth" >/dev/null 2>&1
  chmod 600 "$KEY"
  echo "[start] 证书 SAN: $SAN"
fi

# 先在单进程里完成数据库初始化/迁移，避免 HTTP/HTTPS 两个实例并发建库冲突
python -c "from app.db import get_conn, init_db; init_db(get_conn())" || exit 1

# HTTPS（供"保存到电脑文件夹"使用，8443）
uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile "$KEY" --ssl-certfile "$CRT" &
HTTPS_PID=$!

# HTTP（日常访问，8088）
uvicorn app.main:app --host 0.0.0.0 --port 8088 &
HTTP_PID=$!

echo "[start] HTTP :8088 / HTTPS :8443 已启动"

terminate() { kill "$HTTPS_PID" "$HTTP_PID" 2>/dev/null || true; }
trap terminate TERM INT

# 任意一个服务退出即结束（sh/dash 不支持 wait -n）
wait
