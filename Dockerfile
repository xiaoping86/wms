# 库管易仓库管理系统 — 多阶段 Docker 镜像
# 阶段1：在容器内构建前端静态资源（无需宿主机提前 build）
# 阶段2：Python 运行环境托管 API + 静态资源

# ---------------- 阶段 1：构建前端 ----------------
FROM node:22-alpine AS frontend-build
WORKDIR /src
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---------------- 阶段 2：运行环境 ----------------
FROM python:3.13-slim
WORKDIR /app

ENV WMS_DB=/data/wms.db \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tzdata openssl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/
COPY backend/start.sh /app/start.sh
COPY --from=frontend-build /src/dist /app/frontend/dist

VOLUME ["/data"]

EXPOSE 8088 8443

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fs http://localhost:8088/api/health || exit 1

CMD ["sh", "/app/start.sh"]
