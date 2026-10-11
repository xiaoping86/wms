"""SQLite 数据层：连接管理、建表、种子数据。"""
import os
import sqlite3
import threading
from datetime import datetime, date

# 数据库文件位置：环境变量优先，否则当前目录
DB_PATH = os.environ.get("WMS_DB", os.path.join(os.path.dirname(os.path.dirname(__file__)), "wms.db"))
SCHEMA_VERSION = 1

_INIT_LOCK = threading.Lock()
_INITED = False
_LOCAL = threading.local()
_ALL_CONNS: set = set()
# 局域网多人共用：写锁串行化多表事务，避免交错导致脏数据。
# 注意：每个线程使用独立的 SQLite 连接（WAL 支持多连接并发）。
# 此前全局共用一个连接，多线程并发执行 SQL 会抛出
# sqlite3.InterfaceError: bad parameter or other API misuse。
WRITE_LOCK = threading.Lock()


def get_conn() -> sqlite3.Connection:
    c = getattr(_LOCAL, "conn", None)
    if c is not None:
        return c
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    # WAL：读写不互斥（局域网多人同时查报表/录单据更流畅）
    c.execute("PRAGMA journal_mode = WAL")
    # 写冲突等待 5 秒而不是立刻报 database is locked
    c.execute("PRAGMA busy_timeout = 5000")
    c.execute("PRAGMA synchronous = NORMAL")
    _LOCAL.conn = c
    global _INITED
    with _INIT_LOCK:
        _ALL_CONNS.add(c)
        if not _INITED:
            init_db(c)
            _INITED = True
    return c


def close_all():
    """关闭所有线程的连接（还原数据库、热替换库文件前调用）。"""
    global _LOCAL, _INITED
    with _INIT_LOCK:
        for c in list(_ALL_CONNS):
            try:
                c.close()
            except Exception:
                pass
        _ALL_CONNS.clear()
        _LOCAL = threading.local()
        _INITED = False


def conn() -> sqlite3.Connection:
    return get_conn()


def init_db(c: sqlite3.Connection):
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            name TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, parent_id INTEGER,
            remark TEXT,
            FOREIGN KEY(parent_id) REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS category_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, parent_id INTEGER,
            sortval INTEGER DEFAULT 0, remark TEXT,
            FOREIGN KEY(parent_id) REFERENCES category_classes(id)
        );
        CREATE TABLE IF NOT EXISTS goods_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, parent_id INTEGER,
            remark TEXT,
            FOREIGN KEY(parent_id) REFERENCES goods_categories(id)
        );
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, contact TEXT, phone TEXT,
            address TEXT, utype TEXT DEFAULT 'both', remark TEXT,
            unit_category_id INTEGER, is_default INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS unit_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, parent_id INTEGER,
            remark TEXT,
            FOREIGN KEY(parent_id) REFERENCES unit_categories(id)
        );
        CREATE TABLE IF NOT EXISTS personnel_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, parent_id INTEGER,
            remark TEXT,
            FOREIGN KEY(parent_id) REFERENCES personnel_categories(id)
        );
        CREATE TABLE IF NOT EXISTS warehouses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, address TEXT, contact TEXT, phone TEXT,
            dft TEXT, remark TEXT, warehouse_category_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS warehouse_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, parent_id INTEGER,
            remark TEXT,
            FOREIGN KEY(parent_id) REFERENCES warehouse_categories(id)
        );
        CREATE TABLE IF NOT EXISTS location_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, parent_id INTEGER,
            remark TEXT,
            FOREIGN KEY(parent_id) REFERENCES location_categories(id)
        );
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, warehouse_id INTEGER, remark TEXT,
            location_category_id INTEGER, parent_id INTEGER, dft TEXT DEFAULT '',
            FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
        );
        CREATE TABLE IF NOT EXISTS personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, prole TEXT, phone TEXT,
            unit_id INTEGER, personnel_category_id INTEGER,
            is_default INTEGER DEFAULT 0, remark TEXT
        );
        CREATE TABLE IF NOT EXISTS personnel_titles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL,
            sortval INTEGER DEFAULT 0, remark TEXT
        );
        CREATE TABLE IF NOT EXISTS goods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT NOT NULL, spec TEXT, model TEXT,
            unit TEXT, goods_category_id INTEGER, default_location_id INTEGER,
            min_stock REAL DEFAULT 0, max_stock REAL DEFAULT 0,
            purchase_price REAL DEFAULT 0, sale_price REAL DEFAULT 0,
            in_price REAL DEFAULT 0, out_price REAL DEFAULT 0,
            transfer_price REAL DEFAULT 0, chk_price REAL DEFAULT 0,
            enabled INTEGER DEFAULT 1, remark TEXT,
            FOREIGN KEY(goods_category_id) REFERENCES goods_categories(id),
            FOREIGN KEY(default_location_id) REFERENCES locations(id)
        );
        CREATE TABLE IF NOT EXISTS inbound (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT UNIQUE NOT NULL, date TEXT, unit_id INTEGER,
            warehouse_id INTEGER, operator TEXT, remark TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(unit_id) REFERENCES units(id),
            FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
        );
        CREATE TABLE IF NOT EXISTS inbound_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER, goods_id INTEGER,
            location_id INTEGER, qty REAL DEFAULT 0, price REAL DEFAULT 0, amount REAL DEFAULT 0,
            FOREIGN KEY(doc_id) REFERENCES inbound(id),
            FOREIGN KEY(goods_id) REFERENCES goods(id),
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );
        CREATE TABLE IF NOT EXISTS outbound (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT UNIQUE NOT NULL, date TEXT, unit_id INTEGER,
            warehouse_id INTEGER, operator TEXT, remark TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(unit_id) REFERENCES units(id),
            FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
        );
        CREATE TABLE IF NOT EXISTS outbound_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER, goods_id INTEGER,
            location_id INTEGER, qty REAL DEFAULT 0, price REAL DEFAULT 0, amount REAL DEFAULT 0,
            FOREIGN KEY(doc_id) REFERENCES outbound(id),
            FOREIGN KEY(goods_id) REFERENCES goods(id),
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );
        CREATE TABLE IF NOT EXISTS transfer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT UNIQUE NOT NULL, date TEXT,
            from_warehouse_id INTEGER, to_warehouse_id INTEGER,
            operator TEXT, remark TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(from_warehouse_id) REFERENCES warehouses(id),
            FOREIGN KEY(to_warehouse_id) REFERENCES warehouses(id)
        );
        CREATE TABLE IF NOT EXISTS transfer_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER, goods_id INTEGER,
            from_location_id INTEGER, to_location_id INTEGER,
            qty REAL DEFAULT 0, price REAL DEFAULT 0, amount REAL DEFAULT 0,
            FOREIGN KEY(doc_id) REFERENCES transfer(id),
            FOREIGN KEY(goods_id) REFERENCES goods(id),
            FOREIGN KEY(from_location_id) REFERENCES locations(id),
            FOREIGN KEY(to_location_id) REFERENCES locations(id)
        );
        CREATE TABLE IF NOT EXISTS chk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT UNIQUE NOT NULL, date TEXT, warehouse_id INTEGER,
            operator TEXT, remark TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
        );
        CREATE TABLE IF NOT EXISTS chk_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER, goods_id INTEGER,
            location_id INTEGER, book_qty REAL DEFAULT 0, actual_qty REAL DEFAULT 0,
            price REAL DEFAULT 0, diff_qty REAL DEFAULT 0, diff_amount REAL DEFAULT 0,
            FOREIGN KEY(doc_id) REFERENCES chk(id),
            FOREIGN KEY(goods_id) REFERENCES goods(id),
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );
        CREATE TABLE IF NOT EXISTS initial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT UNIQUE NOT NULL, date TEXT, operator TEXT, remark TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS initial_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER, goods_id INTEGER,
            warehouse_id INTEGER, location_id INTEGER,
            qty REAL DEFAULT 0, price REAL DEFAULT 0, amount REAL DEFAULT 0,
            FOREIGN KEY(doc_id) REFERENCES initial(id),
            FOREIGN KEY(goods_id) REFERENCES goods(id),
            FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );
        CREATE TABLE IF NOT EXISTS boms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL, name TEXT DEFAULT '',
            voltage TEXT DEFAULT '', current TEXT DEFAULT '',
            doc_no TEXT DEFAULT '', remark TEXT DEFAULT '',
            field_defs TEXT, col_defs TEXT, extra TEXT
        );
        CREATE TABLE IF NOT EXISTS bom_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bom_id INTEGER NOT NULL,
            seq INTEGER, qty REAL DEFAULT 1, dwg TEXT DEFAULT '',
            name TEXT DEFAULT '', base TEXT DEFAULT '', remark TEXT DEFAULT '',
            extra TEXT,
            FOREIGN KEY(bom_id) REFERENCES boms(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS borrow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT, date TEXT, goods_id INTEGER, location_id INTEGER,
            qty REAL DEFAULT 0, borrower TEXT, btype TEXT DEFAULT 'lend',
            related_id INTEGER, returned_qty REAL DEFAULT 0, remark TEXT,
            FOREIGN KEY(goods_id) REFERENCES goods(id),
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS op_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT DEFAULT (datetime('now','localtime')),
            username TEXT,
            module TEXT,
            action TEXT,
            detail TEXT
        );
        CREATE TABLE IF NOT EXISTS grid_layouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            grid TEXT NOT NULL,
            widths TEXT,
            width INTEGER,
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(username, grid)
        );
        """
    )
    # 旧库升级：users 增加 职务/启用 列
    cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
    if "title" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN title TEXT")
    if "enabled" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN enabled INTEGER DEFAULT 1")
    if "remark" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN remark TEXT")
    if "permissions" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN permissions TEXT")  # JSON 数组：操作权限键
    # 旧库升级：单据表增加 类别/签名（第一签字、审核人）列
    for tbl in ("inbound", "outbound", "transfer", "chk"):
        dcols = {r["name"] for r in c.execute(f"PRAGMA table_info({tbl})")}
        if "category" not in dcols:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN category TEXT")
        if "sign_a" not in dcols:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN sign_a TEXT")
        if "sign_b" not in dcols:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN sign_b TEXT")
    # 旧库升级：单据明细表增加 备注 列（报表中可直接编辑明细备注）
    for tbl in ("inbound_item", "outbound_item", "transfer_item", "chk_item", "initial_item"):
        dcols = {r["name"] for r in c.execute(f"PRAGMA table_info({tbl})")}
        if "remark" not in dcols:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN remark TEXT")
    # 旧库升级：grid_layouts 增加 width 列（表格横向宽度，0=自适应）
    gcols = {r["name"] for r in c.execute("PRAGMA table_info(grid_layouts)")}
    if "width" not in gcols:
        c.execute("ALTER TABLE grid_layouts ADD COLUMN width INTEGER")
    # 旧库升级：往来单位/工作人员 增加分类、默认、电话等列
    for tbl, col, ddl in (
        ("units", "unit_category_id", "INTEGER"),
        ("units", "is_default", "INTEGER DEFAULT 0"),
        ("personnel", "phone", "TEXT"),
        ("personnel", "personnel_category_id", "INTEGER"),
        ("personnel", "unit_id", "INTEGER"),
        ("personnel", "is_default", "INTEGER DEFAULT 0"),
        ("goods", "in_price", "REAL DEFAULT 0"),
        ("goods", "out_price", "REAL DEFAULT 0"),
        ("goods", "transfer_price", "REAL DEFAULT 0"),
        ("goods", "chk_price", "REAL DEFAULT 0"),
        ("goods", "enabled", "INTEGER DEFAULT 1"),
        ("warehouses", "address", "TEXT"),
        ("warehouses", "contact", "TEXT"),
        ("warehouses", "phone", "TEXT"),
        ("warehouses", "dft", "TEXT"),
        ("warehouses", "warehouse_category_id", "INTEGER"),
        ("locations", "location_category_id", "INTEGER"),
        ("locations", "parent_id", "INTEGER"),
        ("goods", "sortval", "INTEGER DEFAULT 0"),
        ("units", "sortval", "INTEGER DEFAULT 0"),
        ("warehouses", "sortval", "INTEGER DEFAULT 0"),
        ("locations", "sortval", "INTEGER DEFAULT 0"),
        ("personnel", "sortval", "INTEGER DEFAULT 0"),
        ("categories", "sortval", "INTEGER DEFAULT 0"),
        ("goods_categories", "sortval", "INTEGER DEFAULT 0"),
        ("unit_categories", "sortval", "INTEGER DEFAULT 0"),
        ("personnel_categories", "sortval", "INTEGER DEFAULT 0"),
        ("warehouse_categories", "sortval", "INTEGER DEFAULT 0"),
        ("location_categories", "sortval", "INTEGER DEFAULT 0"),
        # 进出类别（原版 LeiBie 表）：是/否 标记列
        ("categories", "zjcb", "TEXT DEFAULT ''"),
        ("categories", "jxtj", "TEXT DEFAULT ''"),
        ("categories", "zjlr", "TEXT DEFAULT ''"),
        ("categories", "csjj", "TEXT DEFAULT ''"),
        ("categories", "xygh", "TEXT DEFAULT ''"),
        ("categories", "kjdh", "TEXT DEFAULT ''"),
        ("categories", "sel", "TEXT DEFAULT ''"),
        # 原版 DanWei/RenYuan 的 select 列：默认单据类型（无/入库单/出库单/调拨单/盘点单）
        ("units", "dft", "TEXT DEFAULT ''"),
        ("personnel", "dft", "TEXT DEFAULT ''"),
        # 原版 KuWei 的 select 列：默认（无/全部/新货物/智能库位）
        ("locations", "dft", "TEXT DEFAULT ''"),
        # BOM 自定义表头字段/明细列：定义 JSON 与扩展值 JSON
        ("boms", "field_defs", "TEXT"),
        ("boms", "col_defs", "TEXT"),
        ("boms", "extra", "TEXT"),
        ("bom_items", "extra", "TEXT"),
        # 进出类别记录所属分类（类别分类树 category_classes）
        ("categories", "class_id", "INTEGER"),
    ):
        pcols = {r["name"] for r in c.execute(f"PRAGMA table_info({tbl})")}
        if col not in pcols:
            c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {ddl}")
    # 类别分类树：原版左树(分类)与右侧类别记录是两套数据。旧库同表实现需迁移拆分
    if c.execute("SELECT COUNT(*) AS n FROM category_classes").fetchone()["n"] == 0:
        old = c.execute("SELECT id, code, name, parent_id, sortval, remark FROM categories ORDER BY COALESCE(sortval,0), id").fetchall()
        if old:
            # 旧库：分类节点与记录同表。按原行拆出同名分类节点（保留id），记录挂到同名节点下
            for r in old:
                c.execute(
                    "INSERT INTO category_classes(id, code, name, parent_id, sortval, remark) VALUES(?,?,?,?,?,?)",
                    (r["id"], r["code"], r["name"], r["parent_id"], r["sortval"], r["remark"]),
                )
            c.execute("UPDATE categories SET class_id=id WHERE class_id IS NULL")
        else:
            # 新库：与原版一致的默认数据（4个分类节点 + 4条类别记录）
            for i2, name in enumerate(("入库类别", "出库类别", "调拨类别", "盘点类别"), 1):
                c.execute("INSERT INTO category_classes(code, name, sortval) VALUES(?,?,?)", (f"FLLB{i2:02d}", name, i2))
            for i2, name in enumerate(("入库类别", "出库类别", "调拨类别", "盘点类别"), 1):
                c.execute("INSERT INTO categories(code, name, class_id, sel) VALUES(?,?,?,?)", (f"LB{i2:03d}", name, i2, "否"))
    c.commit()
    _seed(c)


# ---------- 系统设置 ----------
import json as _json

DEFAULT_SETTINGS = {
    "company_name": "浙江武义瑞峰有限公司",
    "sys_title": "仓库管理系统",
    "cost_method": "moving_avg",      # moving_avg 移动加权平均 | doc_price 单据价即成本
    "cost_tail_adjust": True,          # 成本尾差自动化调整
    "force_recalc_avg": False,         # 进出库强制重算均价
    "est_cost_by_doc_price": True,     # 无成本用单据价暂估
    "wh_cost": False,                  # 分仓库核算存货成本
    "avg_digits": 6, "cost_digits": 2,
    "qty_digits": 2, "price_digits": 2, "amount_digits": 2,
    "qty_pad_zero": False, "price_pad_zero": False,
    "auto_save": True,                 # 操作后自动保存文件
    "doc_no_immutable": True,          # 查询单据不可改单号
    "no_negative_stock": False,        # 出库后不允许负库存
    # 货物资料自定义字段：spec/model 为内置，field1-5 为扩展
    "goods_fields": [
        {"key": "spec",   "label": "规格",  "enabled": True,  "in_list": True,  "required": False, "in_doc": True, "custom_label": ""},
        {"key": "model",  "label": "型号",  "enabled": True,  "in_list": True,  "required": False, "in_doc": True, "custom_label": ""},
        {"key": "field1", "label": "字段1", "enabled": False, "in_list": False, "required": False, "in_doc": False, "custom_label": ""},
        {"key": "field2", "label": "字段2", "enabled": False, "in_list": False, "required": False, "in_doc": False, "custom_label": ""},
        {"key": "field3", "label": "字段3", "enabled": False, "in_list": False, "required": False, "in_doc": False, "custom_label": ""},
        {"key": "field4", "label": "字段4", "enabled": False, "in_list": False, "required": False, "in_doc": False, "custom_label": ""},
        {"key": "field5", "label": "字段5", "enabled": False, "in_list": False, "required": False, "in_doc": False, "custom_label": ""},
    ],
    # 库位管理
    "location_mgmt": True,             # 启用智能化库位管理
    "loc_required_in_goods": True,     # 货物中必填默认库位
    "loc_required_in_doc": True,       # 单据中必填进出库位
    "loc_priority": ["最后期初库位", "最后进库库位", "最小存量库位", "最大存量库位", "货物默认库位", "全局默认库位", "—不显示库位—"],
    # 单据配置
    "docs": {
        "inbound":  {"title": "入 库 单", "rows": 6, "prefix": "RK", "rule": "[前缀][年]-[月][日]-[四位序号]", "show_unit_addr": False},
        "outbound": {"title": "出 库 单", "rows": 6, "prefix": "CK", "rule": "[前缀][年]-[月][日]-[四位序号]", "show_unit_addr": False},
        "transfer": {"title": "调 拨 单", "rows": 6, "prefix": "DB", "rule": "[前缀][年]-[月][日]-[四位序号]", "show_unit_addr": False},
        "check":    {"title": "盘 点 单", "rows": 6, "prefix": "PD", "rule": "[前缀][年]-[月][日]-[四位序号]", "show_unit_addr": False},
        "initial":  {"title": "期 初 库 存", "rows": 6, "prefix": "QC", "rule": "[前缀][年]-[月][日]-[四位序号]", "show_unit_addr": False},
    },
}


def get_settings() -> dict:
    row = fetchone("SELECT value FROM settings WHERE key='app'")
    if not row:
        return dict(DEFAULT_SETTINGS)
    try:
        saved = _json.loads(row["value"])
    except Exception:
        return dict(DEFAULT_SETTINGS)
    merged = dict(DEFAULT_SETTINGS)
    merged.update({k: v for k, v in saved.items() if k != "docs"})
    # docs 按单逐项合并，保证新增字段有默认值
    docs = {k: dict(v) for k, v in DEFAULT_SETTINGS["docs"].items()}
    for k, v in (saved.get("docs") or {}).items():
        if k in docs:
            docs[k].update(v)
    merged["docs"] = docs
    gf = {g["key"]: dict(g) for g in DEFAULT_SETTINGS["goods_fields"]}
    for g in saved.get("goods_fields") or []:
        if g.get("key") in gf:
            gf[g["key"]].update(g)
    merged["goods_fields"] = list(gf.values())
    return merged


def save_settings(data: dict):
    c = conn()
    c.execute(
        "INSERT INTO settings(key,value) VALUES('app',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (_json.dumps(data, ensure_ascii=False),),
    )
    c.commit()


def doc_config(doc_type: str) -> dict:
    """单据类型运行时配置（表名等由 docs.py 管理，这里只取用户设置）。"""
    s = get_settings()
    cfg = dict(s["docs"].get(doc_type, {}))
    if not cfg.get("prefix"):
        cfg["prefix"] = {"inbound": "RK", "outbound": "CK", "transfer": "DB", "check": "PD", "initial": "QC"}.get(doc_type, "DOC")
    return cfg


def _seed(c: sqlite3.Connection):
    # 默认分类（与新旧库无关，缺了就补）
    if c.execute("SELECT COUNT(*) AS n FROM unit_categories").fetchone()["n"] == 0:
        for code, name in (("DWLB01", "供货厂商"), ("DWLB02", "销售客户"), ("DWLB03", "企业部门")):
            c.execute("INSERT INTO unit_categories(code,name) VALUES(?,?)", (code, name))
    if c.execute("SELECT COUNT(*) AS n FROM personnel_categories").fetchone()["n"] == 0:
        for code, name in (
            ("RY01", "供货人"), ("RY02", "领货人"), ("RY03", "调拨人"),
            ("RY04", "盘点人"), ("RY05", "经办人"), ("RY06", "审核人"),
        ):
            c.execute("INSERT INTO personnel_categories(code,name) VALUES(?,?)", (code, name))
    if c.execute("SELECT COUNT(*) AS n FROM personnel_titles").fetchone()["n"] == 0:
        for code, name in (
            ("ZW01", "经理"), ("ZW02", "主管"), ("ZW03", "业务员"),
            ("ZW04", "仓管员"), ("ZW05", "财务"), ("ZW06", "审核人"),
        ):
            c.execute("INSERT INTO personnel_titles(code,name) VALUES(?,?)", (code, name))
    cur = c.execute("SELECT COUNT(*) AS n FROM users")
    if cur.fetchone()["n"] == 0:
        # 默认管理员：admin / admin123
        import hashlib
        pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute(
            "INSERT INTO users(username, password_hash, role, name) VALUES(?,?,?,?)",
            ("admin", pw, "admin", "系统管理员"),
        )
        # 示例基础资料（与原系统演示数据一致）
        c.execute("INSERT INTO warehouses(code,name) VALUES('CK01','主仓库')")
        c.execute("INSERT INTO warehouses(code,name) VALUES('CK02','分仓A')")
        c.execute("INSERT INTO locations(code,name,warehouse_id) VALUES('KW01','默认库位',1)")
        c.execute("INSERT INTO units(code,name,utype) VALUES('DW01','浙江武义瑞峰有限公司','supplier')")
        c.execute("INSERT INTO units(code,name,utype) VALUES('DW02','重庆迅速科技有限公司','customer')")
        c.execute("INSERT INTO goods_categories(code,name) VALUES('LB01','电子类')")
        c.execute(
            "INSERT INTO goods(code,name,spec,unit,goods_category_id,default_location_id,purchase_price,sale_price,min_stock,max_stock) "
            "VALUES('HW01','示例货物A','标准','个',1,1,10,15,5,100)"
        )
        c.commit()


# ---------- 通用工具 ----------
def q(sql: str, params=()):
    return conn().execute(sql, params).fetchall()


def i(sql: str, params=()):
    cur = conn().execute(sql, params)
    conn().commit()
    return cur.lastrowid


def u(sql: str, params=()):
    cur = conn().execute(sql, params)
    conn().commit()
    return cur.rowcount


def fetchone(sql: str, params=()):
    return conn().execute(sql, params).fetchone()


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def today() -> str:
    return date.today().isoformat()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_op(username: str, module: str, action: str, detail: str = ""):
    """操作日志：所有数据操作记录保存在服务器数据库（op_logs 表）。"""
    try:
        conn().execute(
            "INSERT INTO op_logs(username,module,action,detail) VALUES(?,?,?,?)",
            (username or "", module or "", action or "", str(detail or "")[:500]),
        )
        conn().commit()
    except Exception:
        pass  # 日志失败不影响业务


def gen_doc_no(prefix: str) -> str:
    """当日单号：前缀+日期+四位序号。取 MAX 而非 COUNT——删除中间单据后不会复用已有单号。"""
    d = date.today().strftime("%Y%m%d")
    like = f"{prefix}{d}%"
    m = fetchone(
        "SELECT MAX(doc_no) AS m FROM ("
        "SELECT doc_no FROM inbound WHERE doc_no LIKE ? "
        "UNION ALL SELECT doc_no FROM outbound WHERE doc_no LIKE ? "
        "UNION ALL SELECT doc_no FROM transfer WHERE doc_no LIKE ? "
        "UNION ALL SELECT doc_no FROM chk WHERE doc_no LIKE ? "
        "UNION ALL SELECT doc_no FROM initial WHERE doc_no LIKE ? )",
        (like, like, like, like, like),
    )["m"]
    n = int(str(m)[-4:]) if m and str(m)[-4:].isdigit() else 0
    return f"{prefix}{d}{str(n + 1).zfill(4)}"


def dicts(rows):
    return rows_to_dicts(rows)
