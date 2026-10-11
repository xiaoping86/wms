"""基础资料通用 CRUD 路由工厂。"""
import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from ..db import conn, rows_to_dicts, fetchone, log_op
from ..deps import get_current_user, require_perm

# 表 -> 路由前缀
TABLES = {
    "goods": "goods",
    "units": "units",
    "warehouses": "warehouses",
    "locations": "locations",
    "personnel": "personnel",
    "categories": "categories",
    "category-classes": "category_classes",
    "goods-categories": "goods_categories",
    "unit-categories": "unit_categories",
    "personnel-categories": "personnel_categories",
    "personnel-titles": "personnel_titles",
    "warehouse-categories": "warehouse_categories",
    "location-categories": "location_categories",
}

# 表中文名（删除提示用）
TBL_CN = {
    "goods": "货物资料", "units": "往来单位", "warehouses": "仓库", "locations": "库位",
    "personnel": "工作人员", "categories": "进出类别", "users": "账号",
    "category_classes": "类别分类",
    "goods_categories": "货物分类", "unit_categories": "单位分类", "personnel_categories": "人员分类",
    "personnel_titles": "人员职务",
    "warehouse_categories": "仓库分类", "location_categories": "库位分类",
    "inbound": "入库单", "outbound": "出库单", "transfer": "调拨单", "chk": "盘点单", "initial": "期初单",
    "inbound_item": "入库单", "outbound_item": "出库单", "transfer_item": "调拨单",
    "chk_item": "盘点单", "initial_item": "期初单",
}

# 分类表 -> 引用它的(资料表, 字段)（部分分类字段无外键约束，需主动检查）
CAT_USED_BY = {
    "category_classes": [("categories", "class_id")],
    "goods_categories": [("goods", "goods_category_id")],
    "unit_categories": [("units", "unit_category_id")],
    "personnel_categories": [("personnel", "personnel_category_id")],
    "warehouse_categories": [("warehouses", "warehouse_category_id")],
    "location_categories": [("locations", "location_category_id")],
}


def _references(table: str, item_id: int):
    """找出引用了 table 表 item_id 行的数据，返回 [(中文名, 数量)]。"""
    c = conn()
    covered = set(CAT_USED_BY.get(table, []))  # 分类列由下方专门检查，避免重复
    result = {}
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for t in tables:
        if t == table:  # 自引用（下级分类）另行处理
            continue
        try:
            fks = c.execute(f"PRAGMA foreign_key_list({t})").fetchall()
        except Exception:
            continue
        cols = []
        for fk in fks:
            if (fk[2] or "").lower() == table.lower() and (t, fk[3]) not in covered:
                cols.append(fk[3])
        if not cols:
            continue
        where = " OR ".join(f"{col}=?" for col in cols)
        try:
            n = c.execute(f"SELECT COUNT(*) n FROM {t} WHERE {where}", [item_id] * len(cols)).fetchone()["n"]
        except Exception:
            continue
        if n:
            cn = TBL_CN.get(t, t)
            result[cn] = result.get(cn, 0) + n
    # 分类表：无外键约束的资料字段
    for t, col in CAT_USED_BY.get(table, []):
        try:
            n = c.execute(f"SELECT COUNT(*) n FROM {t} WHERE {col}=?", (item_id,)).fetchone()["n"]
        except Exception:
            continue
        if n:
            cn = TBL_CN.get(t, t)
            result[cn] = result.get(cn, 0) + n
    return list(result.items())

# 编码留空时的自动编码前缀（对应原版"留空则自动编码"）
CODE_PREFIX = {
    "goods": "HW", "units": "DW", "warehouses": "CK", "locations": "KW",
    "personnel": "RY", "categories": "LB",
    "category_classes": "FLLB",
    "goods_categories": "LB", "unit_categories": "DWLB",
    "personnel_categories": "RY", "personnel_titles": "ZW", "warehouse_categories": "CKLB",
    "location_categories": "KWLB",
}


def _auto_code(table: str, body: dict):
    """编码留空则自动编码：前缀 + 3位序号。"""
    if "code" not in _columns(table) or "code" not in body or (body.get("code") or "").strip():
        return
    pre = CODE_PREFIX.get(table, "BM")
    row = conn().execute(
        f"SELECT code FROM {table} WHERE code LIKE ? ORDER BY id DESC LIMIT 1", (pre + "%",)).fetchone()
    n = 1
    if row and row["code"] and row["code"][len(pre):].isdigit():
        n = int(row["code"][len(pre):]) + 1
    body["code"] = f"{pre}{n:03d}"


def _columns(table: str):
    cur = conn().execute(f"PRAGMA table_info({table})")
    return [r["name"] for r in cur.fetchall()]


def _normalize(body: dict):
    """空字符串的外键/关联字段转为 None，避免 sqlite 外键约束直接报 500。"""
    for k, v in list(body.items()):
        if k.endswith("_id") and v == "":
            body[k] = None


def make_router(url: str, table: str):
    router = APIRouter(prefix=f"/api/{url}", tags=[url])
    # 写操作权限键：与前端"账号权限"对应（分类表归并到其主资料权限）
    PERM_KEY = {
        "goods": "goods", "units": "units", "warehouses": "warehouses", "locations": "locations",
        "personnel": "personnel", "personnel-titles": "personnel",
        "categories": "categories", "category-classes": "categories",
        "goods-categories": "goods-categories", "unit-categories": "units",
        "personnel-categories": "personnel", "warehouse-categories": "warehouses",
        "location-categories": "locations",
    }
    write_dep = Depends(require_perm(PERM_KEY.get(url, url)))

    @router.get("")
    def list_items(q: Optional[str] = None, user=Depends(get_current_user)):
        cols = _columns(table)
        if q:
            clauses = []
            params = []
            for c in ("name", "code"):
                if c in cols:
                    clauses.append(f"{c} LIKE ?")
                    params.append(f"%{q}%")
            where = f"WHERE {' OR '.join(clauses)}" if clauses else ""
            rows = conn().execute(f"SELECT * FROM {table} {where} ORDER BY COALESCE(sortval,0), id", params).fetchall()
        else:
            rows = conn().execute(f"SELECT * FROM {table} ORDER BY COALESCE(sortval,0), id").fetchall()
        return rows_to_dicts(rows)

    @router.get("/{item_id}")
    def get_item(item_id: int, user=Depends(get_current_user)):
        row = fetchone(f"SELECT * FROM {table} WHERE id=?", (item_id,))
        if not row:
            raise HTTPException(404, "记录不存在")
        return dict(row)

    @router.post("")
    def create_item(body: dict, user=write_dep):
        _auto_code(table, body)
        _normalize(body)
        cols = [c for c in _columns(table) if c != "id" and c in body]
        vals = [body[c] for c in cols]
        ph = ",".join("?" * len(cols))
        sql = f"INSERT INTO {table}({','.join(cols)}) VALUES({ph})"
        try:
            lid = conn().execute(sql, vals).lastrowid
            if "sortval" in _columns(table):
                conn().execute(f"UPDATE {table} SET sortval=(SELECT COALESCE(MAX(sortval),0)+1 FROM {table}) WHERE id=?", (lid,))
            conn().commit()
        except sqlite3.IntegrityError:
            conn().rollback()
            raise HTTPException(400, "保存失败：所选关联数据不存在或已被删除，请重新选择后再保存")
        log_op(user["username"], table, "新增", f"id={lid} " + "; ".join(f"{c}={body[c]}" for c in cols if c in ("code", "name")))
        return {"id": lid, **body}

    @router.put("/{item_id}")
    def update_item(item_id: int, body: dict, user=write_dep):
        _normalize(body)
        cols = [c for c in _columns(table) if c != "id" and c in body]
        if not cols:
            raise HTTPException(400, "无有效字段")
        sets = ",".join(f"{c}=?" for c in cols)
        vals = [body[c] for c in cols] + [item_id]
        try:
            conn().execute(f"UPDATE {table} SET {sets} WHERE id=?", vals)
            conn().commit()
        except sqlite3.IntegrityError:
            conn().rollback()
            raise HTTPException(400, "保存失败：所选关联数据不存在或已被删除，请重新选择后再保存")
        log_op(user["username"], table, "修改", f"id={item_id} 字段: {','.join(cols)}")
        return {"ok": True, "id": item_id}

    @router.post("/reorder")
    def reorder(body: dict, user=write_dep):
        """按给定 id 顺序重写 sortval（原版工具条上移/下移）。"""
        ids = body.get("ids") or []
        if "sortval" not in _columns(table):
            raise HTTPException(400, "该数据不支持排序")
        for k, iid in enumerate(ids):
            conn().execute(f"UPDATE {table} SET sortval=? WHERE id=?", (k, iid))
        conn().commit()
        log_op(user["username"], table, "排序", f"共{len(ids)}条")
        return {"ok": True}

    @router.delete("/{item_id}")
    def delete_item(item_id: int, user=write_dep):
        c = conn()
        # 下级分类检查（自引用）
        if "parent_id" in _columns(table):
            n = c.execute(f"SELECT COUNT(*) n FROM {table} WHERE parent_id=?", (item_id,)).fetchone()["n"]
            if n:
                raise HTTPException(400, f"无法删除：该{TBL_CN.get(table, '分类')}下还有 {n} 个下级，请先删除或移走下级")
        # 被其他数据引用检查（中文提示）
        refs = _references(table, item_id)
        if refs:
            detail = "；".join(f"{cn} {n} 条" for cn, n in refs)
            raise HTTPException(400, f"无法删除：被以下数据引用 —— {detail}。请先删除或修改这些数据")
        try:
            c.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
            c.commit()
        except Exception as e:
            raise HTTPException(400, f"删除失败：{e}")
        log_op(user["username"], table, "删除", f"id={item_id}")
        return {"ok": True}

    return router


routers = [make_router(url, tbl) for url, tbl in TABLES.items()]
