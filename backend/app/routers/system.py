"""系统路由：认证、用户权限、借还、备份恢复、导入。"""
import csv
import io
import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from ..db import conn, fetchone, DB_PATH, get_settings, save_settings, log_op
from ..deps import (hash_pw, verify_pw, needs_rehash, make_token, get_current_user, require_admin,
                    require_perm, login_too_many, login_fail, login_ok)
from ..schemas import LoginReq, ChangePwdReq, UserCreate, UserUpdate, BorrowCreate, ProfileUpdate

# 操作权限键 -> 显示名（与原版一致，树形展示）
PERMISSION_TREE = [
    {"key": "settings", "label": "系统设置"},
    {"key": "users", "label": "账号权限"},
    {"key": "data", "label": "数据管理"},
    {"key": "personnel", "label": "工作人员"},
    {"key": "categories", "label": "进出类别"},
    {"key": "warehouses", "label": "仓库信息"},
    {"key": "locations", "label": "库区库位"},
    {"key": "units", "label": "往来单位"},
    {"key": "goods", "label": "货物资料"},
    {"key": "goods-categories", "label": "货物分类"},
    {"key": "initial", "label": "期初库存"},
    {"key": "inbound", "label": "入库单"},
    {"key": "outbound", "label": "出库单"},
    {"key": "transfer", "label": "调拨单"},
    {"key": "check", "label": "盘点单"},
    {"key": "docquery", "label": "单据查询"},
    {"key": "reports", "label": "报表中心"},
]

router = APIRouter(prefix="/api", tags=["system"])


def _perms_of(row) -> list:
    raw = row["permissions"] if "permissions" in row.keys() else None
    if not raw:
        return []
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except Exception:
        return []


# ---------- 认证 ----------
@router.post("/auth/login")
def login(body: LoginReq):
    if login_too_many(body.username):
        raise HTTPException(429, "失败次数过多，请 5 分钟后再试")
    row = fetchone("SELECT * FROM users WHERE username=?", (body.username,))
    if not row or not verify_pw(body.password, row["password_hash"]):
        login_fail(body.username)
        log_op(body.username or "?", "系统", "登录失败", "用户名或密码错误")
        raise HTTPException(401, "用户名或密码错误")
    if dict(row).get("enabled", 1) == 0:
        raise HTTPException(403, "该账号已被禁用，请联系管理员")
    u = dict(row)
    # 旧格式口令哈希自动升级为 PBKDF2
    if needs_rehash(u.get("password_hash") or ""):
        conn().execute("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(body.password), u["id"]))
        conn().commit()
    login_ok(body.username)
    token = make_token(u["username"])
    log_op(u["username"], "系统", "登录", f"角色 {u['role']}")
    u.pop("password_hash", None)  # 口令哈希不出网
    return {"token": token, "user": {"id": u["id"], "username": u["username"], "role": u["role"],
                                     "name": u["name"], "title": u.get("title"), "permissions": _perms_of(row)}}


@router.get("/auth/me")
def me(user=Depends(get_current_user)):
    return user


@router.post("/auth/change-password")
def change_pwd(body: ChangePwdReq, user=Depends(get_current_user)):
    row = fetchone("SELECT * FROM users WHERE id=?", (user["id"],))
    if not verify_pw(body.old_password, row["password_hash"]):
        raise HTTPException(400, "原密码错误")
    conn().execute("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(body.new_password), user["id"]))
    conn().commit()
    log_op(user["username"], "系统", "修改密码")
    return {"ok": True}


# ---------- 个人设置 ----------
@router.put("/auth/profile")
def update_profile(body: ProfileUpdate, user=Depends(get_current_user)):
    sets, vals = [], []
    if body.name is not None:
        sets.append("name=?"); vals.append(body.name)
    if body.title is not None:
        sets.append("title=?"); vals.append(body.title)
    if body.new_password:
        row = fetchone("SELECT password_hash FROM users WHERE id=?", (user["id"],))
        if not body.old_password or not verify_pw(body.old_password, row["password_hash"]):
            raise HTTPException(400, "原密码错误")
        sets.append("password_hash=?"); vals.append(hash_pw(body.new_password))
    if sets:
        conn().execute(f"UPDATE users SET {','.join(sets)} WHERE id=?", vals + [user["id"]])
        conn().commit()
    log_op(user["username"], "个人设置", "保存", ",".join(s.split("=")[0] for s in sets))
    return {"ok": True}


# ---------- 系统设置 ----------
@router.get("/system/settings")
def read_settings(user=Depends(get_current_user)):
    return get_settings()


@router.put("/system/settings", dependencies=[Depends(require_perm("settings"))])
def write_settings(body: dict, user=Depends(get_current_user)):
    save_settings(body)
    log_op(user["username"], "系统设置", "保存", "主题/字段/单据配置等")
    return get_settings()


@router.get("/system/login-bg")
def public_login_bg():
    """登录页用：免登录读取登录背景图（壁纸），返回 dataURL 或空字符串。"""
    st = get_settings() or {}
    return {"login_bg": st.get("login_bg") or "", "theme": st.get("theme") or "",
            "sys_title": st.get("sys_title") or "", "company_name": st.get("company_name") or ""}


# ---------- 用户/权限 ----------
@router.get("/permissions/tree")
def permission_tree(user=Depends(get_current_user)):
    """操作权限树（编辑账号窗口用）。"""
    return PERMISSION_TREE


@router.get("/users", dependencies=[Depends(require_perm("users"))])
def list_users():
    rows = conn().execute("SELECT id,username,role,name,title,enabled,remark,permissions,created_at FROM users ORDER BY id").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["permissions"] = _perms_of(r)
        out.append(d)
    return out


@router.post("/users", dependencies=[Depends(require_perm("users"))])
def create_user(body: UserCreate, user=Depends(get_current_user)):
    if fetchone("SELECT id FROM users WHERE username=?", (body.username,)):
        raise HTTPException(400, "用户名已存在")
    lid = conn().execute(
        "INSERT INTO users(username,password_hash,role,name,title,enabled,remark,permissions) VALUES(?,?,?,?,?,?,?,?)",
        (body.username, hash_pw(body.password), body.role, body.name, body.title,
         1 if body.enabled else 0, body.remark,
         json.dumps(body.permissions or [], ensure_ascii=False))).lastrowid
    conn().commit()
    log_op(user["username"], "账号权限", "新增账号", f"{body.username}({body.name or ''}) 权限{len(body.permissions or [])}项")
    return {"id": lid}


@router.put("/users/{uid}", dependencies=[Depends(require_perm("users"))])
def update_user(uid: int, body: UserUpdate, user=Depends(get_current_user)):
    sets, vals = [], []
    if body.role is not None:
        sets.append("role=?"); vals.append(body.role)
    if body.name is not None:
        sets.append("name=?"); vals.append(body.name)
    if body.title is not None:
        sets.append("title=?"); vals.append(body.title)
    if body.enabled is not None:
        sets.append("enabled=?"); vals.append(1 if body.enabled else 0)
    if body.remark is not None:
        sets.append("remark=?"); vals.append(body.remark)
    if body.password:
        sets.append("password_hash=?"); vals.append(hash_pw(body.password))
    if body.permissions is not None:
        sets.append("permissions=?"); vals.append(json.dumps(body.permissions, ensure_ascii=False))
    if sets:
        conn().execute(f"UPDATE users SET {','.join(sets)} WHERE id=?", vals + [uid])
        conn().commit()
    log_op(user["username"], "账号权限", "修改账号", f"id={uid} 字段: {','.join(s.split('=')[0] for s in sets)}")
    return {"ok": True}


@router.delete("/users/{uid}", dependencies=[Depends(require_admin)])
def delete_user(uid: int, user=Depends(require_admin)):
    conn().execute("DELETE FROM users WHERE id=? AND role<>'admin'", (uid,))
    conn().commit()
    log_op(user["username"], "账号权限", "删除账号", f"id={uid}")
    return {"ok": True}


# ---------- 操作日志 ----------
@router.get("/op-logs", dependencies=[Depends(require_admin)])
def op_logs(start: str = None, end: str = None, user: str = None, q: str = None, limit: int = 500):
    """查询服务器端操作日志（仅管理员）。"""
    where, params = ["1=1"], []
    if start:
        where.append("time>=?"); params.append(start)
    if end:
        where.append("time<=?"); params.append(end + " 23:59:59")
    if user:
        where.append("username=?"); params.append(user)
    if q:
        where.append("(module LIKE ? OR action LIKE ? OR detail LIKE ?)")
        params.extend([f"%{q}%"] * 3)
    rows = conn().execute(
        f"SELECT * FROM op_logs WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT {int(limit)}",
        params).fetchall()
    users = [r["username"] for r in conn().execute(
        "SELECT DISTINCT username FROM op_logs ORDER BY username").fetchall()]
    return {"logs": [dict(r) for r in rows], "users": users}


# ---------- 借还 ----------
@router.post("/borrow")
def borrow(body: BorrowCreate, user=Depends(get_current_user)):
    from ..db import WRITE_LOCK
    c = conn()
    date = body.date
    with WRITE_LOCK:  # 单号生成+写入原子化，防多人同时借还撞单号
        doc_no = "JH" + (date or "").replace("-", "") + str(c.execute(
            "SELECT COUNT(*) n FROM borrow WHERE date=?", (date,)).fetchone()["n"] + 1).zfill(3)
        if body.btype == "lend":
            lid = c.execute(
                "INSERT INTO borrow(doc_no,date,goods_id,location_id,qty,borrower,btype,remark) VALUES(?,?,?,?,?,?,?,?)",
                (doc_no, date, body.goods_id, body.location_id, body.qty, body.borrower, "lend", body.remark)).lastrowid
            c.commit()
            log_op(user["username"], "借还", "借出", f"单号{doc_no} goods_id={body.goods_id} 数量{body.qty}")
            return {"id": lid, "doc_no": doc_no}
        else:
            # 归还：冲减最近一笔未还完的借出
            rec = c.execute(
                "SELECT * FROM borrow WHERE goods_id=? AND btype='lend' AND returned_qty<qty ORDER BY id LIMIT 1",
                (body.goods_id,)).fetchone()
            if not rec:
                raise HTTPException(400, "没有可归还的借出记录")
            remain = rec["qty"] - rec["returned_qty"]
            back = min(body.qty, remain)
            c.execute("UPDATE borrow SET returned_qty=returned_qty+? WHERE id=?", (back, rec["id"]))
            lid = c.execute(
                "INSERT INTO borrow(doc_no,date,goods_id,location_id,qty,borrower,btype,related_id,remark) VALUES(?,?,?,?,?,?,?,?,?)",
                (doc_no, date, body.goods_id, body.location_id, back, body.borrower, "return", rec["id"], body.remark)).lastrowid
            c.commit()
            log_op(user["username"], "借还", "归还", f"单号{doc_no} goods_id={body.goods_id} 数量{back}")
            return {"id": lid, "doc_no": doc_no}


@router.get("/borrow")
def list_borrow(goods_id: int = None, user=Depends(get_current_user)):
    sql = "SELECT * FROM borrow WHERE 1=1"
    params = []
    if goods_id:
        sql += " AND goods_id=?"
        params.append(goods_id)
    sql += " ORDER BY id DESC"
    rows = conn().execute(sql, params).fetchall()
    goods = {r["id"]: r for r in conn().execute("SELECT id,code,name,unit FROM goods").fetchall()}
    out = []
    for r in rows:
        rec = dict(r)
        g = goods.get(r["goods_id"], {})
        rec["goods_code"] = g.get("code")
        rec["goods_name"] = g.get("name")
        rec["unit"] = g.get("unit")
        rec["unreturned"] = round((r["qty"] or 0) - (r["returned_qty"] or 0), 2)
        out.append(rec)
    return out


# ---------- 备份 / 恢复 ----------
def _safe_backup_copy(dst_path: str):
    """用 SQLite backup API 生成一致性快照。直接复制主文件在 WAL 模式下会得到空库。"""
    import sqlite3
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dst_path)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


def daily_backup(keep: int = 30):
    """每日自动备份：容器启动时若当天还没有自动备份则生成一份；保留最近 keep 份。"""
    try:
        bdir = os.path.join(os.path.dirname(DB_PATH) or ".", "backups")
        os.makedirs(bdir, exist_ok=True)
        today = datetime.now().strftime("%Y%m%d")
        dst = os.path.join(bdir, f"auto_{today}.db")
        if not os.path.exists(dst):
            _safe_backup_copy(dst)
        autos = sorted(f for f in os.listdir(bdir) if f.startswith("auto_") and f.endswith(".db"))
        for f in autos[:-keep]:
            try:
                os.remove(os.path.join(bdir, f))
            except OSError:
                pass
        # 操作日志防无限增长：仅保留最近 5 万条
        try:
            c = conn()
            c.execute("DELETE FROM op_logs WHERE id < (SELECT COALESCE(MAX(id),0) FROM op_logs) - 50000")
            c.commit()
        except Exception:
            pass
    except Exception:
        pass  # 备份失败不阻塞启动


@router.get("/backup", dependencies=[Depends(require_perm("data"))])
def backup(user=Depends(get_current_user)):
    import tempfile
    from starlette.background import BackgroundTask
    if not os.path.exists(DB_PATH):
        raise HTTPException(404, "数据库文件不存在")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fd, tmp = tempfile.mkstemp(suffix=f"_wms_backup_{stamp}.db")
    os.close(fd)
    _safe_backup_copy(tmp)
    size = os.path.getsize(tmp)
    log_op(user["username"], "数据管理", "备份到本机", f"大小={size}")
    return FileResponse(tmp, filename=f"wms_backup_{stamp}.db",
                        background=BackgroundTask(os.remove, tmp))


@router.get("/backup-dirs", dependencies=[Depends(require_perm("data"))])
def backup_dirs(path: str = None):
    """浏览服务器目录：返回当前目录与其子目录，用于备份位置选择（仅限数据目录内）。"""
    import glob as _glob
    base = os.path.abspath(os.path.dirname(DB_PATH) or "/")
    cur = os.path.abspath(path) if path else base
    if cur != base and not cur.startswith(base + os.sep):
        raise HTTPException(403, "只能浏览数据目录及其子目录")
    if not os.path.isdir(cur):
        raise HTTPException(400, "目录不存在")
    try:
        dirs = sorted(d for d in os.listdir(cur) if os.path.isdir(os.path.join(cur, d)) and not d.startswith("."))
    except PermissionError:
        dirs = []
    files = []
    for f in sorted(_glob.glob(os.path.join(cur, "*.db"))):
        st = os.stat(f)
        files.append({"name": os.path.basename(f), "size": st.st_size,
                      "time": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")})
    return {"current": cur, "dirs": dirs, "files": files}


@router.post("/backup-to", dependencies=[Depends(require_perm("data"))])
def backup_to(body: dict, user=Depends(get_current_user)):
    """备份数据库到服务器指定目录。body = {path}"""
    import shutil
    path = (body.get("path") or "").strip()
    if not path:
        raise HTTPException(400, "请指定备份位置")
    dst_dir = os.path.abspath(path)
    os.makedirs(dst_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"wms_backup_{stamp}.db"
    dst = os.path.join(dst_dir, fname)
    _safe_backup_copy(dst)
    size = os.path.getsize(dst)
    log_op(user["username"], "数据管理", "备份", f"位置={dst_dir} 文件={fname} 大小={size}")
    return {"ok": True, "path": dst_dir, "file": fname, "size": size}


@router.post("/restore", dependencies=[Depends(require_perm("data"))])
def restore(file: UploadFile = File(...), user=Depends(require_perm("data"))):
    import importlib
    dbmod = importlib.import_module("app.db")
    data = file.file.read()
    # 校验是有效的 SQLite 数据库文件，避免误传任意文件毁库
    if not data.startswith(b"SQLite format 3\x00"):
        raise HTTPException(400, "所选文件不是有效的数据库备份文件（应为 .db 备份）")
    # 还原前自动做一次安全备份，还原错了还能退回来
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bdir = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(bdir, exist_ok=True)
        _safe_backup_copy(os.path.join(bdir, f"before_restore_{stamp}.db"))
    except Exception:
        pass
    dbmod.close_all()  # 关闭所有线程连接，避免旧连接残留 WAL 句柄
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with open(DB_PATH, "wb") as f:
        f.write(data)
    # 删除残留 WAL/SHM，否则旧 WAL 数据会叠加到还原后的库上导致数据错乱
    for suffix in ("-wal", "-shm"):
        try:
            os.remove(DB_PATH + suffix)
        except FileNotFoundError:
            pass
    dbmod.get_conn()  # 重新初始化
    log_op(user["username"], "数据管理", "还原数据库", f"{file.filename} {len(data)}字节")
    return {"ok": True, "size": len(data)}


# ---------- 初始化 ----------
@router.post("/system/reset", dependencies=[Depends(require_perm("data"))])
def reset(mode: str = "business", user=Depends(get_current_user)):
    """初始化数据。mode=business 仅清空业务单据与借还记录；mode=all 连基础资料一并清空（均保留用户账号）。"""
    biz = ["inbound_item", "inbound", "outbound_item", "outbound", "transfer_item", "transfer",
           "chk_item", "chk", "initial_item", "initial", "borrow"]
    master = ["goods", "goods_categories", "units", "unit_categories",
              "locations", "location_categories", "warehouses", "warehouse_categories",
              "personnel", "personnel_categories", "personnel_titles",
              "categories", "category_classes", "bom_items", "boms"]
    tables = biz + (master if mode == "all" else [])
    c = conn()
    for t in tables:
        c.execute(f"DELETE FROM {t}")
    c.execute("DELETE FROM sqlite_sequence WHERE name IN (%s)" % ",".join("?" * len(tables)), tables)
    c.commit()
    log_op(user["username"], "数据管理", "系统初始化", f"mode={mode} 清空{len(tables)}张表")
    return {"ok": True, "cleared": tables}


# ---------- CSV 导入 ----------
_HEADER_MAP = {
    "goods": {
        "code": ["编码", "code"], "name": ["名称", "name"], "spec": ["规格", "spec"],
        "model": ["型号", "model"], "unit": ["单位", "unit"], "category": ["分类", "category"],
        "min_stock": ["最低库存", "min_stock"], "max_stock": ["最高库存", "max_stock"],
        "purchase_price": ["入库单价", "purchase_price"], "sale_price": ["出库单价", "sale_price"],
    },
    "units": {
        "code": ["编码", "code"], "name": ["名称", "name"], "contact": ["联系人", "contact"],
        "phone": ["电话", "phone"], "address": ["地址", "address"], "utype": ["类型", "utype"],
    },
}


@router.post("/import/{kind}", dependencies=[Depends(require_perm("data"))])
def import_csv(kind: str, file: UploadFile = File(...), user=Depends(get_current_user)):
    if kind not in _HEADER_MAP:
        raise HTTPException(400, "不支持的导入类型")
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    hmap = _HEADER_MAP[kind]
    # 建立 表头中文->字段 的反查
    rev = {}
    for field, names in hmap.items():
        for n in names:
            rev[n] = field
    cols = {c: rev.get(c.strip()) for c in (reader.fieldnames or [])}
    table = "goods" if kind == "goods" else "units"
    allcols = list(hmap.keys())
    # 分类名 -> id 缓存
    cat_cache = {}
    cnt = 0
    c = conn()
    for row in reader:
        vals = {}
        for h, field in cols.items():
            if field:
                vals[field] = (row.get(h) or "").strip()
        if not vals.get("name"):
            continue
        # 分类转换
        if kind == "goods" and vals.get("category"):
            cn = vals["category"]
            if cn not in cat_cache:
                r = c.execute("SELECT id FROM goods_categories WHERE name=?", (cn,)).fetchone()
                cat_cache[cn] = r["id"] if r else None
            vals["goods_category_id"] = cat_cache[cn]
        ins = {k: (vals.get(k) or (0 if k in ("min_stock", "max_stock", "purchase_price", "sale_price") else ""))
               for k in allcols if k in ("code", "name", "spec", "model", "unit", "contact", "phone", "address", "utype", "goods_category_id", "min_stock", "max_stock", "purchase_price", "sale_price")}
        keys = list(ins.keys())
        ph = ",".join("?" * len(keys))
        c.execute(f"INSERT INTO {table}({','.join(keys)}) VALUES({ph})", [ins[k] for k in keys])
        cnt += 1
    c.commit()
    log_op(user["username"], "数据管理", "批量导入", f"{kind} 导入{cnt}条")
    return {"imported": cnt}
