"""表格列宽 + 表格横向宽度布局：保存在服务器（按当前登录用户），不存浏览器。

前端 initColResize 会在表格首次出现时 GET 该用户对该表格(grid)的列宽与表格宽度；
拖拽列宽或横向手柄结束后 PUT 保存。grid 由前端 data-grid-key 决定（每个表格唯一）。

- widths: 各列像素宽度数组 [120, 90, ...]，空数组或 null 表示未设（自适应）
- width:  表格整体像素宽度（整数），0 或 null 表示自适应父容器（不锁死）
"""
import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..deps import get_current_user
from ..db import fetchone, conn

router = APIRouter(prefix="/api/grid-layout", tags=["grid-layout"])


class SaveBody(BaseModel):
    grid: str
    widths: list  # [120, 90, ...] 按列顺序的像素宽度
    width: int = 0  # 表格整体像素宽度；0 表示自适应（未锁死）


@router.get("")
def get_layout(grid: str, user=Depends(get_current_user)):
    row = fetchone(
        "SELECT widths, width FROM grid_layouts WHERE username=? AND grid=?",
        (user["username"], grid),
    )
    widths = []
    width = 0
    if row:
        if row["widths"]:
            try:
                widths = [float(w) for w in json.loads(row["widths"])]
            except Exception:
                widths = []
        if row["width"]:
            width = int(row["width"])
    return {"grid": grid, "widths": widths, "width": width}


@router.put("")
def save_layout(body: SaveBody, user=Depends(get_current_user)):
    widths = [max(36, int(round(float(w)))) for w in (body.widths or [])]
    w = max(0, int(body.width or 0))  # 0 表示自适应
    txt = json.dumps(widths)
    conn().execute(
        "INSERT INTO grid_layouts(username, grid, widths, width, updated_at) "
        "VALUES(?, ?, ?, ?, datetime('now','localtime')) "
        "ON CONFLICT(username, grid) DO UPDATE SET "
        "widths=excluded.widths, width=excluded.width, updated_at=datetime('now','localtime')",
        (user["username"], body.grid, txt, w),
    )
    conn().commit()
    return {"ok": True, "grid": body.grid, "widths": widths, "width": w}
