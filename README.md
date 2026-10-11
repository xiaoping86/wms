# 仓库管理系统（Web 版）

将原 Excel 宏 + XLL 仓库管理系统，重构为 **前端 + 后端 + 数据库** 的 Web 应用，可部署在 Docker Desktop，通过局域网 `http://<本机IP>:8088` 访问。所有原系统功能均已实现。

## 功能清单（对应原 Excel 系统）

| 模块 | 功能 |
|------|------|
| 基础资料 | 货物资料、往来单位、货物分类、类别、仓库、库位、人员（含分类/单位/库位等下拉引用） |
| 业务单据 | 入库单、出库单、调拨单、盘点单、期初库存（行项目录入，自动影响库存） |
| 报表中心 | 库存查询（含低/高/无库位预警）、分仓库存、进销存汇总、利润表、进出明细、借还管理 |
| 系统管理 | 账号权限（增删改 + 职务 + 启用/禁用）、数据备份与恢复、货物/单位 CSV 批量导入、数据初始化 |
| 系统设置 | 单位信息、单据参数（标题/单号前缀/默认行数）、成本参数、显示参数、货物字段（启用/列表/必填/自定义名称）、库位参数 |
| 个人设置 | 账号资料（名称/职务）、修改密码（原密码校验）、注销 |
| 其它 | 按期间统计、CSV 导出 |

库存、进销存、利润均由单据流水**实时聚合**计算，保证账实一致。

## 技术架构

- **后端**：FastAPI + SQLite（标准库，零原生编译依赖）
- **前端**：Vue 3 + Vite + Element Plus
- **部署**：单容器（Python 运行后端 API 并托管前端静态资源），监听 `0.0.0.0:8088`
- **数据持久化**：SQLite 文件挂载于 `/data` 卷，重启不丢数据

## 目录结构

```
wms-app/
├── backend/            # FastAPI 后端
│   ├── app/           # 应用代码（db / routers / deps / schemas）
│   └── requirements.txt
├── frontend/          # Vue 前端源码（容器构建期自动编译）
├── Dockerfile          # 多阶段构建（自动构建前端 + Python 运行）
├── docker-compose.yml
├── deploy.bat         # Windows 一键部署脚本（双击运行）
└── deploy.sh           # Linux / macOS 一键部署脚本
```

## 默认账号

- 管理员：`admin` / `admin123`（首次登录后请修改密码）

## 本地开发运行

```bash
# 后端
cd backend && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8088

# 前端（另开终端）
cd frontend && npm install && npm run dev   # 开发服务器 5173，已代理 /api 到 8088
# 生产前端构建：npm run build  → 产物在 frontend/dist
```

## 一键部署（推荐）

仓库已附带一键部署脚本，自动完成「构建镜像 → 启动容器 → 等待就绪 → 打印访问地址」全流程，**无需在宿主机预先构建前端**（前端在容器内自动编译）。

- **Windows**：双击 `deploy.bat`（需已安装并启动 Docker Desktop）。
- **Linux / macOS**：终端执行 `bash deploy.sh`（或 `chmod +x deploy.sh && ./deploy.sh`）。

脚本会自动检测 Docker 是否运行、端口占用情况，并提示本机与局域网访问地址。

> **当前部署端口为 8089**（因本机 8088 已被其他项目容器 `winding-params` 占用），compose 映射为 `"8089:8088"`。访问 `http://localhost:8089`，局域网 `http://<本机IP>:8089`。

> 也可手动执行下方命令完成部署。

## Docker 手动部署（局域网访问）

镜像采用**多阶段构建**：前端在容器内自动 `npm install && npm run build`，无需宿主机预构建。

```bash
cd wms-app
docker compose up -d --build
```

启动后访问 `http://localhost:8088`。**局域网其他电脑**访问 `http://<本机局域网IP>:8088`（如 `http://192.168.x.x:8088`）。
若无法访问，请检查：
1. 本机防火墙是否放行 8088 端口；
2. `docker compose` 端口映射是否为 `8088:8088`；
3. 容器是否健康：`docker ps` 查看 STATUS 含 `healthy`。
4. 若 8088 被占用，编辑 `docker-compose.yml` 将 `"8088:8088"` 改为空闲端口（如 `"8099:8088"`），再运行 `deploy` 脚本或 `docker compose up -d`。

## 数据备份与恢复

- 进入「系统管理 → 数据备份」可下载 `wms_backup.db`；
- 上传备份文件即可一键恢复（恢复会覆盖当前数据库，需管理员权限）；
- 数据库文件实际位于容器 `/data/wms.db`，对应 compose 卷 `wms-data`，可直接备份该卷。

## 与原 Excel 系统的差异说明

- 原系统的「列配置（LiePei）」为界面布局定制功能，Web 版采用响应式表格统一呈现，未单独保留该配置界面；
- 原 XLL 原生引擎（C++）已用 FastAPI + SQLite 重写，业务逻辑等价，且数据可查询、可备份、可审计；
- 权限模型简化为「管理员 / 普通用户」两级。
