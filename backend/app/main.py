"""FastAPI 应用入口：装配路由、静态托管与 SPA 回退。前后端同源部署，无需跨域放行。"""
import os
import mimetypes
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .db import init_db
from .routers import master, docs, reports, system, bom, grid
from .deps import get_current_user

DIST = os.environ.get("WMS_DIST", os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist"))

app = FastAPI(title="库管易仓库管理系统 (Web)", version="1.0.0")

# master.routers 是列表，逐个包含
for r in master.routers:
    app.include_router(r)
for r in docs.routers:
    app.include_router(r)
app.include_router(reports.router)
app.include_router(bom.router)
app.include_router(system.router)
app.include_router(grid.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "dist": os.path.isdir(DIST)}


@app.get("/{full_path:path}")
async def spa(full_path: str):
    if full_path.startswith("api") or full_path.startswith("docs"):
        raise HTTPException(404, "not found")
    dist_dir = DIST
    if os.path.isdir(dist_dir):
        candidate = os.path.normpath(os.path.join(dist_dir, full_path))
        # 防目录穿越
        if candidate.startswith(os.path.normpath(dist_dir)) and os.path.isfile(candidate):
            if os.path.dirname(candidate) == os.path.normpath(os.path.join(dist_dir, "assets")):
                # 带内容哈希的静态资源：长缓存（文件名变即 URL 变，永不冲突）
                return FileResponse(candidate, media_type=mimetypes.guess_type(candidate)[0] or "application/octet-stream",
                                    headers={"Cache-Control": "public, max-age=31536000, immutable"})
            return FileResponse(candidate, media_type=mimetypes.guess_type(candidate)[0] or "application/octet-stream",
                                headers={"Cache-Control": "no-cache"})
        index = os.path.join(dist_dir, "index.html")
        if os.path.exists(index):
            # 入口页强制协商缓存（ETag 304），确保发新版后浏览器立刻拿到新界面
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return HTTPException(404, "前端未构建，请先执行前端构建")


@app.on_event("startup")
def startup():
    from .db import get_conn
    get_conn()
    # 每日自动备份（保留最近30份），数据多一道保险
    try:
        system.daily_backup()
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)
