"""业务单据路由：入库 / 出库 / 调拨 / 盘点 / 期初。"""
from fastapi import APIRouter, HTTPException, Depends
import sqlite3
from ..db import conn, fetchone, rows_to_dicts, gen_doc_no, today, doc_config, log_op, get_settings, WRITE_LOCK
from ..deps import get_current_user, require_perm
from ..schemas import DocCreate

# 单据类型配置
DOCS = {
    "inbound": dict(tbl="inbound", itbl="inbound_item", prefix="RK",
                    hcols=["date", "unit_id", "category", "warehouse_id", "operator", "sign_a", "sign_b", "remark"],
                    icols=["goods_id", "location_id", "qty", "price", "amount"]),
    "outbound": dict(tbl="outbound", itbl="outbound_item", prefix="CK",
                     hcols=["date", "unit_id", "category", "warehouse_id", "operator", "sign_a", "sign_b", "remark"],
                     icols=["goods_id", "location_id", "qty", "price", "amount"]),
    "transfer": dict(tbl="transfer", itbl="transfer_item", prefix="DB",
                     hcols=["date", "category", "from_warehouse_id", "to_warehouse_id", "operator", "sign_a", "sign_b", "remark"],
                     icols=["goods_id", "from_location_id", "to_location_id", "qty", "price", "amount"]),
    "check": dict(tbl="chk", itbl="chk_item", prefix="PD",
                  hcols=["date", "category", "warehouse_id", "operator", "sign_a", "sign_b", "remark"],
                  icols=["goods_id", "location_id", "book_qty", "actual_qty", "price"],
                  is_check=True),
    "initial": dict(tbl="initial", itbl="initial_item", prefix="QC",
                    hcols=["date", "operator", "remark"],
                    icols=["goods_id", "warehouse_id", "location_id", "qty", "price", "amount", "remark"]),
}


def make_router(name: str, cfg: dict):
    router = APIRouter(prefix=f"/api/{name}", tags=[name])
    # 权限键与前端"账号权限"一致：inbound/outbound/transfer/check/initial
    write_dep = Depends(require_perm(name))

    def _wh_stock_map(c, date, exclude_doc=None):
        """各(货物,仓库)在 date（含）前的账面库存。"""
        ex = f" AND h.id != {int(exclude_doc)}" if exclude_doc else ""
        rows = c.execute(f"""
        SELECT goods_id, wh, SUM(qty) q FROM (
          SELECT i.goods_id, i.warehouse_id wh, i.qty FROM initial_item i JOIN initial h ON h.id=i.doc_id WHERE h.date<=?
          UNION ALL
          SELECT i.goods_id, h.warehouse_id, i.qty FROM inbound_item i JOIN inbound h ON h.id=i.doc_id WHERE h.date<=?{ex}
          UNION ALL
          SELECT i.goods_id, h.warehouse_id, -i.qty FROM outbound_item i JOIN outbound h ON h.id=i.doc_id WHERE h.date<=?{ex}
          UNION ALL
          SELECT i.goods_id, src.warehouse_id, -i.qty FROM transfer_item i JOIN transfer h ON h.id=i.doc_id
               JOIN locations src ON src.id=i.from_location_id WHERE h.date<=?{ex}
          UNION ALL
          SELECT i.goods_id, dst.warehouse_id, i.qty FROM transfer_item i JOIN transfer h ON h.id=i.doc_id
               JOIN locations dst ON dst.id=i.to_location_id WHERE h.date<=?{ex}
          UNION ALL
          SELECT i.goods_id, l.warehouse_id, i.diff_qty FROM chk_item i JOIN chk h ON h.id=i.doc_id
               JOIN locations l ON l.id=i.location_id WHERE h.date<=?{ex}
        ) GROUP BY goods_id, wh""", [date] * 6).fetchall()
        return {(r["goods_id"], r["wh"]): (r["q"] or 0) for r in rows}

    def _check_negative(c, name, body, doc_id=None):
        """设置开启"出库后不允许负库存"时，出库/调拨保存前校验库存。"""
        if name not in ("outbound", "transfer"):
            return
        st = get_settings()
        if not st.get("no_negative_stock"):
            return
        date = body.date or today()
        stock = _wh_stock_map(c, date, exclude_doc=doc_id)
        gnames = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM goods").fetchall()}
        wn = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM warehouses").fetchall()}
        lack = []
        for it in body.items:
            qty = it.qty or 0
            if qty <= 0:
                continue
            if name == "outbound":
                wid = body.warehouse_id
            else:
                loc = getattr(it, "from_location_id", None)
                wid = c.execute("SELECT warehouse_id FROM locations WHERE id=?", (loc,)).fetchone()
                wid = wid["warehouse_id"] if wid else None
            if wid is None:
                continue
            avail = stock.get((it.goods_id, wid), 0)
            if avail - qty < 0:
                lack.append(f"{gnames.get(it.goods_id, it.goods_id)}（可用 {avail}，需 {qty}）")
        if lack:
            raise HTTPException(400, "出库后不允许负库存：库存不足 - " + "；".join(lack[:5]))

    @router.get("")
    def list_docs(unit_id: int = None, warehouse_id: int = None, start: str = None, end: str = None, user=Depends(get_current_user)):
        where, params = ["1=1"], []
        if unit_id:
            where.append("unit_id=?"), params.append(unit_id)
        if warehouse_id:
            where.append("(warehouse_id=? OR from_warehouse_id=? OR to_warehouse_id=?)"), params.extend([warehouse_id, warehouse_id, warehouse_id])
        if start:
            where.append("date>=?"), params.append(start)
        if end:
            where.append("date<=?"), params.append(end)
        rows = conn().execute(
            f"SELECT * FROM {cfg['tbl']} WHERE {' AND '.join(where)} ORDER BY id DESC", params
        ).fetchall()
        return rows_to_dicts(rows)

    @router.get("/config")
    def get_config(user=Depends(get_current_user)):
        """单据运行配置（标题/前缀/默认行数等，来自系统设置）。"""
        return doc_config(name)

    @router.get("/next-no")
    def next_no(user=Depends(get_current_user)):
        """预览下一单据号（不占用序号）。"""
        return {"doc_no": gen_doc_no(doc_config(name)["prefix"])}

    @router.get("/{doc_id}")
    def get_doc(doc_id: int, user=Depends(get_current_user)):
        h = fetchone(f"SELECT * FROM {cfg['tbl']} WHERE id=?", (doc_id,))
        if not h:
            raise HTTPException(404, "单据不存在")
        items = conn().execute(f"SELECT * FROM {cfg['itbl']} WHERE doc_id=?", (doc_id,)).fetchall()
        return {"header": dict(h), "items": rows_to_dicts(items)}

    @router.post("")
    def create_doc(body: DocCreate, user=write_dep):
        # 数量/单价不允许负数（原版同样不允许负数量录入）
        for it in body.items:
            if (it.qty or 0) < 0:
                raise HTTPException(400, "数量不能为负数，请检查单据明细")
            if (it.price or 0) < 0:
                raise HTTPException(400, "单价不能为负数，请检查单据明细")
        c = conn()
        with WRITE_LOCK:  # 局域网多人同时保存：单号生成+落库原子化
            _check_negative(c, name, body)
            date = body.date or today()
            hcols = cfg["hcols"]
            # 生成单号并插入表头；撞 UNIQUE（他端刚插入同号）自动重取新号，最多 3 次
            for attempt in range(3):
                doc_no = gen_doc_no(doc_config(name)["prefix"])
                hvals = []
                for col in hcols:
                    v = getattr(body, col, None)
                    if col == "date":
                        v = date
                    hvals.append(v)
                try:
                    cur = c.execute(
                        f"INSERT INTO {cfg['tbl']}(doc_no,{','.join(hcols)}) VALUES(?,{','.join('?'*len(hcols))})",
                        [doc_no] + hvals,
                    )
                    break
                except sqlite3.IntegrityError:
                    c.rollback()
                    if attempt == 2:
                        raise HTTPException(409, "单据号生成冲突，请稍后重试")
            doc_id = cur.lastrowid
            try:
                for it in body.items:
                    iv = []
                    for col in cfg["icols"]:
                        if cfg.get("is_check") and col == "price":
                            iv.append(it.price or 0)
                        else:
                            iv.append(getattr(it, col, None) or 0)
                    # 补充金额/差异
                    extra = []
                    if cfg.get("is_check"):
                        book = it.book_qty or 0
                        actual = it.actual_qty or 0
                        price = it.price or 0
                        diff_qty = actual - book
                        diff_amount = round(diff_qty * price, 2)
                        iv = [it.goods_id, it.location_id, book, actual, price]
                        extra = [diff_qty, diff_amount]
                        c.execute(
                            f"INSERT INTO {cfg['itbl']}(doc_id,goods_id,location_id,book_qty,actual_qty,price,diff_qty,diff_amount) VALUES(?,?,?,?,?,?,?,?)",
                            [doc_id] + iv + extra,
                        )
                    else:
                        # 计算金额
                        qty = it.qty or 0
                        price = it.price or 0
                        amount = round(qty * price, 2)
                        base = [doc_id]
                        for col in cfg["icols"]:
                            if col == "amount":
                                base.append(amount)
                            elif col in ("remark", "note"):
                                base.append(getattr(it, col, None) or "")
                            elif col.endswith("_id"):
                                base.append(getattr(it, col, None))  # 外键可空，不能写 0
                            else:
                                base.append(getattr(it, col, None) or 0)
                        ph = ",".join("?" * len(base))
                        c.execute(f"INSERT INTO {cfg['itbl']}({','.join(['doc_id']+cfg['icols'])}) VALUES({ph})", base)
                c.commit()
            except sqlite3.IntegrityError:
                c.rollback()
                raise HTTPException(400, "保存失败：单据中的货物/仓库/库位等关联数据不存在或已被删除，请检查后重试")
            except Exception:
                c.rollback()
                raise
        amt = sum((it.qty or 0) * (it.price or 0) for it in body.items)
        log_op(user["username"], name, "保存单据", f"{doc_no} 共{len(body.items)}行 金额{round(amt, 2)}")
        return {"id": doc_id, "doc_no": doc_no}

    @router.put("/{doc_id}")
    def update_doc(doc_id: int, body: DocCreate, user=write_dep):
        """单据更新：表头覆盖，明细整体替换（期初等资料型单据编辑用）。"""
        c = conn()
        if not fetchone(f"SELECT id FROM {cfg['tbl']} WHERE id=?", (doc_id,)):
            raise HTTPException(404, "单据不存在")
        for it in body.items:
            if (it.qty or 0) < 0:
                raise HTTPException(400, "数量不能为负数，请检查单据明细")
        _check_negative(c, name, body, doc_id=doc_id)
        vals = []
        for col in cfg["hcols"]:
            v = getattr(body, col, None)
            if col == "date":
                v = body.date or today()
            vals.append(v)
        c.execute(f"UPDATE {cfg['tbl']} SET {','.join(f'{col}=?' for col in cfg['hcols'])} WHERE id=?", vals + [doc_id])
        c.execute(f"DELETE FROM {cfg['itbl']} WHERE doc_id=?", (doc_id,))
        for it in body.items:
            qty = it.qty or 0
            price = it.price or 0
            amount = round(qty * price, 2)
            base = [doc_id]
            for col in cfg["icols"]:
                if col == "amount":
                    base.append(amount)
                elif col in ("remark", "note"):
                    base.append(getattr(it, col, None) or "")
                elif col.endswith("_id"):
                    base.append(getattr(it, col, None))  # 外键可空，不能写 0
                else:
                    base.append(getattr(it, col, None) or 0)
            ph = ",".join("?" * len(base))
            c.execute(f"INSERT INTO {cfg['itbl']}({','.join(['doc_id']+cfg['icols'])}) VALUES({ph})", base)
        try:
            c.commit()
        except sqlite3.IntegrityError:
            c.rollback()
            raise HTTPException(400, "保存失败：单据中的货物/仓库/库位等关联数据不存在或已被删除，请检查后重试")
        amt = sum((it.qty or 0) * (it.price or 0) for it in body.items)
        log_op(user["username"], name, "修改单据", f"#{doc_id} 共{len(body.items)}行 金额{round(amt, 2)}")
        return {"ok": True, "id": doc_id}

    @router.delete("/{doc_id}")
    def delete_doc(doc_id: int, user=write_dep):
        c = conn()
        with WRITE_LOCK:
            c.execute(f"DELETE FROM {cfg['itbl']} WHERE doc_id=?", (doc_id,))
            c.execute(f"DELETE FROM {cfg['tbl']} WHERE id=?", (doc_id,))
            c.commit()
        log_op(user["username"], name, "删除单据", f"id={doc_id}")
        return {"ok": True}

    return router


routers = [make_router(n, c) for n, c in DOCS.items()]
