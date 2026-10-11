"""报表与库存计算路由。库存由单据流水实时聚合，保证账实一致。"""
from fastapi import APIRouter, HTTPException, Depends
from ..db import conn, log_op
from ..deps import get_current_user, require_perm

router = APIRouter(prefix="/api", tags=["reports"])

# 全部流水（带方向、单据号、按采购价的成本）。amount 已带符号，cost 为 qty*采购价（已带符号）。
MOVEMENT_CTE = """
WITH m AS (
  SELECT h.doc_no, h.date, '期初' AS type, i.goods_id, i.warehouse_id, i.location_id,
         i.qty AS qty, i.price AS price, i.amount AS amount, 1 AS sgn, i.qty*g.purchase_price AS cost,
         NULL AS category, h.operator AS operator, NULL AS sign_a, NULL AS sign_b, NULL AS unit_id,
         i.id AS item_id, h.id AS doc_id, 'initial' AS src,
         i.remark AS item_remark, h.remark AS doc_remark
  FROM initial_item i JOIN initial h ON h.id=i.doc_id JOIN goods g ON g.id=i.goods_id
  UNION ALL
  SELECT h.doc_no, h.date, '入库', i.goods_id, h.warehouse_id, i.location_id,
         i.qty, i.price, i.amount, 1, i.qty*g.purchase_price,
         h.category, h.operator, h.sign_a, h.sign_b, h.unit_id,
         i.id, h.id, 'inbound', i.remark, h.remark
  FROM inbound_item i JOIN inbound h ON h.id=i.doc_id JOIN goods g ON g.id=i.goods_id
  UNION ALL
  SELECT h.doc_no, h.date, '出库', i.goods_id, h.warehouse_id, i.location_id,
         -i.qty, i.price, -i.amount, -1, -i.qty*g.purchase_price,
         h.category, h.operator, h.sign_a, h.sign_b, h.unit_id,
         i.id, h.id, 'outbound', i.remark, h.remark
  FROM outbound_item i JOIN outbound h ON h.id=i.doc_id JOIN goods g ON g.id=i.goods_id
  UNION ALL
  SELECT h.doc_no, h.date, '调拨出', i.goods_id, src.warehouse_id, i.from_location_id,
         -i.qty, i.price, -i.amount, -1, -i.qty*g.purchase_price,
         h.category, h.operator, h.sign_a, h.sign_b, NULL,
         i.id, h.id, 'transfer', i.remark, h.remark
  FROM transfer_item i JOIN transfer h ON h.id=i.doc_id JOIN locations src ON src.id=i.from_location_id
       JOIN goods g ON g.id=i.goods_id
  UNION ALL
  SELECT h.doc_no, h.date, '调拨入', i.goods_id, dst.warehouse_id, i.to_location_id,
         i.qty, i.price, i.amount, 1, i.qty*g.purchase_price,
         h.category, h.operator, h.sign_a, h.sign_b, NULL,
         i.id, h.id, 'transfer', i.remark, h.remark
  FROM transfer_item i JOIN transfer h ON h.id=i.doc_id JOIN locations dst ON dst.id=i.to_location_id
       JOIN goods g ON g.id=i.goods_id
  UNION ALL
  SELECT h.doc_no, h.date, '盘点', i.goods_id, l.warehouse_id, i.location_id,
         i.diff_qty, i.price, i.diff_amount,
         CASE WHEN i.diff_qty>=0 THEN 1 ELSE -1 END, i.diff_qty*g.purchase_price,
         h.category, h.operator, h.sign_a, h.sign_b, NULL,
         i.id, h.id, 'chk', i.remark, h.remark
  FROM chk_item i JOIN chk h ON h.id=i.doc_id JOIN locations l ON l.id=i.location_id
       JOIN goods g ON g.id=i.goods_id
)
"""


def _maps():
    wh = {r["id"]: r["name"] for r in conn().execute("SELECT id,name FROM warehouses").fetchall()}
    loc = {r["id"]: r["name"] for r in conn().execute("SELECT id,name FROM locations").fetchall()}
    goods = {r["id"]: dict(r) for r in conn().execute(
        "SELECT id,code,name,spec,model,unit,min_stock,max_stock,purchase_price,sale_price,remark FROM goods").fetchall()}
    return wh, loc, goods


def _goods_ids_by_cat(cid):
    """货物分类(含全部下级)关联的货物 id 集合；cid 为空返回 None 表示不过滤。"""
    if not cid:
        return None
    rows = conn().execute("SELECT id,parent_id FROM goods_categories").fetchall()
    ids = {cid}
    changed = True
    while changed:
        changed = False
        for r in rows:
            if r["parent_id"] in ids and r["id"] not in ids:
                ids.add(r["id"]); changed = True
    ph = ",".join("?" * len(ids))
    return {r["id"] for r in conn().execute(
        f"SELECT id FROM goods WHERE goods_category_id IN ({ph})", tuple(ids)).fetchall()}


def _flt_goods(out, goods_id=None, category_id=None, gidkey="gid"):
    """按 货物/货物分类(含下级) 过滤报表行。"""
    ids = _goods_ids_by_cat(category_id)
    if ids is not None:
        out = [r for r in out if r[gidkey] in ids]
    if goods_id:
        out = [r for r in out if r[gidkey] == goods_id]
    return out


def _merge_rows(out, gidkey, keys, whkey):
    """显示分仓=关：按货物合并各仓库行（数量/成本类累加，仓库列清空）。"""
    merged, order = {}, []
    for r in out:
        k = r[gidkey]
        if k not in merged:
            m = dict(r); m[whkey] = ""; merged[k] = m; order.append(k)
        else:
            m = merged[k]
            for c in keys:
                m[c] = round((m[c] or 0) + (r[c] or 0), 2)
    return [merged[k] for k in order]


def _status(qty, g):
    min_s = g.get("min_stock") or 0
    max_s = g.get("max_stock") or 0
    if min_s > 0 and qty < min_s:
        return "低"
    if max_s > 0 and qty > max_s:
        return "高"
    return "正常"


@router.get("/inventory")
def inventory(warehouse_id: int = None, status: str = None, q: str = None,
              goods_id: int = None, category_id: int = None,
              filter_zero: int = 0, by_wh: int = 1, user=Depends(get_current_user)):
    sql = MOVEMENT_CTE + """
    , agg AS (
      SELECT goods_id, warehouse_id, location_id, SUM(qty) qty, SUM(cost) amt
      FROM m GROUP BY goods_id, warehouse_id, location_id
    )
    SELECT g.id, g.code, g.name, g.unit, g.min_stock, g.max_stock, g.remark,
           a.warehouse_id, a.location_id, COALESCE(a.qty,0) qty, COALESCE(a.amt,0) amt
    FROM goods g LEFT JOIN agg a ON g.id=a.goods_id
    """
    wh, loc, goods = _maps()
    rows = conn().execute(sql).fetchall()
    # 先聚到 货物+仓库 级（原版显示分仓粒度，不再按库位拆多行）
    agg, order = {}, []
    for r in rows:
        k = (r["id"], r["warehouse_id"])
        if k not in agg:
            agg[k] = {"qty": 0.0, "amt": 0.0, "no_loc": True}
            order.append(k)
        agg[k]["qty"] += r["qty"] or 0
        agg[k]["amt"] += r["amt"] or 0
        if r["location_id"]:
            agg[k]["no_loc"] = False
    out = []
    for k in order:
        g = goods.get(k[0], {})
        qty, amt = round(agg[k]["qty"], 2), round(agg[k]["amt"], 2)
        wid = k[1]
        rec = {"id": k[0], "gid": k[0], "code": g.get("code"), "name": g.get("name"),
               "spec": g.get("spec"), "model": g.get("model"), "unit": g.get("unit"),
               "min_stock": g.get("min_stock"), "max_stock": g.get("max_stock"),
               "remark": g.get("remark") or "",
               "warehouse_id": wid, "warehouse_name": wh.get(wid) or ("无" if wid is None else ""),
               "qty": qty, "amt": amt,
               "status": "无库位" if agg[k]["no_loc"] else _status(qty, g)}
        out.append(rec)
    out = _flt_goods(out, goods_id, category_id, "gid")
    if warehouse_id:
        out = [x for x in out if x["warehouse_id"] == warehouse_id]
    if filter_zero:
        out = [x for x in out if x["qty"]]
    if by_wh == 0:
        out = _merge_rows(out, "gid", ["qty", "amt"], "warehouse_name")
    if status:
        out = [x for x in out if x["status"] == status]
    if q:
        out = [x for x in out if (q in (x["name"] or "")) or (q in (x["code"] or ""))]
    return out


@router.get("/inventory/by-warehouse")
def inventory_by_warehouse(user=Depends(get_current_user)):
    sql = MOVEMENT_CTE + """
    , agg AS (
      SELECT goods_id, warehouse_id, SUM(qty) qty, SUM(cost) amt
      FROM m GROUP BY goods_id, warehouse_id
    )
    SELECT warehouse_id, COUNT(*) kinds, SUM(qty) qty, SUM(amt) amt
    FROM agg GROUP BY warehouse_id
    """
    wh, _, _ = _maps()
    rows = conn().execute(sql).fetchall()
    return [{"warehouse_id": r["warehouse_id"], "warehouse_name": wh.get(r["warehouse_id"], "无"),
             "kinds": r["kinds"], "qty": r["qty"], "amt": round(r["amt"] or 0, 2)} for r in rows]


@router.get("/reports/inout")
def inout(start: str = None, end: str = None, goods_id: int = None, direction: str = None,
          doc_type: str = None, doc_category: str = None, category_id: int = None,
          warehouse_id: int = None, unit_id: int = None, person: str = None,
          operator: str = None, user=Depends(get_current_user)):
    sql = MOVEMENT_CTE + "SELECT * FROM m WHERE 1=1"
    params = []
    if start:
        sql += " AND date>=?"; params.append(start)
    if end:
        sql += " AND date<=?"; params.append(end)
    if goods_id:
        sql += " AND goods_id=?"; params.append(goods_id)
    if direction == "in":
        sql += " AND sgn=1"
    elif direction == "out":
        sql += " AND sgn=-1"
    if doc_type == "调拨":
        sql += " AND type IN ('调拨出','调拨入')"
    elif doc_type:
        sql += " AND type=?"; params.append(doc_type)
    if doc_category:
        sql += " AND category LIKE ?"; params.append(f"%{doc_category}%")
    if warehouse_id:
        sql += " AND warehouse_id=?"; params.append(warehouse_id)
    if unit_id:
        sql += " AND unit_id=?"; params.append(unit_id)
    if person:
        sql += " AND sign_a LIKE ?"; params.append(f"%{person}%")
    if operator:
        sql += " AND operator LIKE ?"; params.append(f"%{operator}%")
    sql += " ORDER BY date, doc_no"
    wh, loc, goods = _maps()
    units = {r["id"]: r["name"] for r in conn().execute("SELECT id,name FROM units").fetchall()}
    rows = conn().execute(sql, params).fetchall()
    out = []
    for r in rows:
        g = goods.get(r["goods_id"], {})
        qty = r["qty"] or 0
        amt = r["amount"] or 0
        out.append({
            "gid": r["goods_id"],
            "date": r["date"], "code": g.get("code"), "name": g.get("name"),
            "spec": g.get("spec"), "model": g.get("model"), "unit": g.get("unit"),
            "doc_type": r["type"], "category": r["category"] or "",
            "direction": "进" if (r["sgn"] or 0) > 0 else "出",
            "qty": round(abs(qty), 2), "price": round(r["price"] or 0, 2),
            "amount": round(abs(amt), 2),
            "avg_price": round(abs(amt) / abs(qty), 2) if qty else 0,
            "cost": round(abs(r["cost"] or 0), 2),
            "doc_no": r["doc_no"], "unit_name": units.get(r["unit_id"], "") if r["unit_id"] else "",
            "sign_a": r["sign_a"] or "", "operator": r["operator"] or "", "sign_b": r["sign_b"] or "",
            "warehouse_name": wh.get(r["warehouse_id"], "无"), "location_name": loc.get(r["location_id"], "无库位"),
            "remark": r["item_remark"] or "", "doc_remark": r["doc_remark"] or "",
            "item_id": r["item_id"], "doc_id": r["doc_id"], "src": r["src"],
        })
    return _flt_goods(out, None, category_id, "gid")


@router.get("/reports/jxc")
def jxc(start: str = None, end: str = None, goods_id: int = None, category_id: int = None,
        warehouse_id: int = None, no_move: int = 0, filter_zero: int = 0, by_wh: int = 1,
        user=Depends(get_current_user)):
    """进销存：按货物+仓库列出期初/进货/出货/结存（无流水的货物也列出，与原版一致）。"""
    s = start or "0000-01-01"
    e = end or "9999-12-31"
    sql = MOVEMENT_CTE + """
    , mv AS (
      SELECT m.goods_id, m.warehouse_id, m.date, m.qty, m.cost, m.amount, m.type, m.sgn FROM m
    ), agg AS (
      SELECT goods_id, warehouse_id,
        COALESCE(SUM(CASE WHEN date < :s THEN qty ELSE 0 END),0) begin_qty,
        COALESCE(SUM(CASE WHEN date < :s THEN cost ELSE 0 END),0) begin_cost,
        COALESCE(SUM(CASE WHEN date>=:s AND date<=:e AND sgn=1 THEN qty ELSE 0 END),0) in_qty,
        COALESCE(SUM(CASE WHEN date>=:s AND date<=:e AND sgn=1 THEN cost ELSE 0 END),0) in_cost,
        COALESCE(SUM(CASE WHEN date>=:s AND date<=:e AND sgn=-1 THEN -qty ELSE 0 END),0) out_qty,
        COALESCE(SUM(CASE WHEN date>=:s AND date<=:e AND sgn=-1 THEN -cost ELSE 0 END),0) out_cost,
        COALESCE(SUM(CASE WHEN date>=:s AND date<=:e AND type='出库' THEN -amount ELSE 0 END),0) period_sale
      FROM mv GROUP BY goods_id, warehouse_id
    )
    SELECT g.id AS gid, g.code, g.name, g.spec, g.model, g.unit, a.warehouse_id,
      a.begin_qty, a.begin_cost, a.in_qty, a.in_cost, a.out_qty, a.out_cost, a.period_sale
    FROM goods g LEFT JOIN agg a ON a.goods_id = g.id
    ORDER BY g.code, g.id, a.warehouse_id
    """
    rows = conn().execute(sql, {"s": s, "e": e}).fetchall()
    wh, _, _ = _maps()
    MERGE_KEYS = ["begin_qty", "begin_cost", "in_qty", "in_cost", "out_qty", "out_cost", "end_qty", "end_cost"]
    out = []
    for r in rows:
        if warehouse_id and r["warehouse_id"] != warehouse_id:
            continue
        begin_qty = r["begin_qty"] or 0
        in_qty = r["in_qty"] or 0
        out_qty = r["out_qty"] or 0
        end_qty = begin_qty + in_qty - out_qty
        begin_cost = r["begin_cost"] or 0
        in_cost = r["in_cost"] or 0
        out_cost = r["out_cost"] or 0
        end_cost = begin_cost + in_cost - out_cost
        out.append({
            "gid": r["gid"], "code": r["code"], "name": r["name"],
            "spec": r["spec"], "model": r["model"], "unit": r["unit"],
            "warehouse": wh.get(r["warehouse_id"], "") if r["warehouse_id"] else "",
            "begin_qty": round(begin_qty, 2), "begin_cost": round(begin_cost, 2),
            "in_qty": round(in_qty, 2), "in_cost": round(in_cost, 2),
            "out_qty": round(out_qty, 2), "out_cost": round(out_cost, 2),
            "period_sale": round(r["period_sale"] or 0, 2),
            "end_qty": round(end_qty, 2), "end_cost": round(end_cost, 2),
        })
    out = _flt_goods(out, goods_id, category_id, "gid")
    if by_wh == 0:
        out = _merge_rows(out, "gid", MERGE_KEYS, "warehouse")
    if no_move:
        out = [x for x in out if x["begin_qty"] or x["in_qty"] or x["out_qty"]]
    if filter_zero:
        out = [x for x in out if x["end_qty"]]
    return out


@router.get("/reports/inout-summary")
def inout_summary(start: str = None, end: str = None, goods_id: int = None, category_id: int = None,
                  warehouse_id: int = None, doc_category: str = None, unit_id: int = None,
                  person: str = None, by_wh: int = 1, user=Depends(get_current_user)):
    """进出汇总：按货物+仓库汇总期间进/出数量、单据金额与成本。无流水的货物也列出（与原版一致）。"""
    s = start or "0000-01-01"
    e = end or "9999-12-31"
    sql = MOVEMENT_CTE + """
    , agg AS (
      SELECT goods_id, warehouse_id,
        COALESCE(SUM(CASE WHEN sgn=1  AND date>=:s AND date<=:e THEN qty    ELSE 0 END),0) in_qty,
        COALESCE(SUM(CASE WHEN sgn=1  AND date>=:s AND date<=:e THEN amount ELSE 0 END),0) in_amt,
        COALESCE(SUM(CASE WHEN sgn=1  AND date>=:s AND date<=:e THEN cost   ELSE 0 END),0) in_cost,
        COALESCE(SUM(CASE WHEN sgn=-1 AND date>=:s AND date<=:e THEN -qty    ELSE 0 END),0) out_qty,
        COALESCE(SUM(CASE WHEN sgn=-1 AND date>=:s AND date<=:e THEN -amount ELSE 0 END),0) out_amt,
        COALESCE(SUM(CASE WHEN sgn=-1 AND date>=:s AND date<=:e THEN -cost  ELSE 0 END),0) out_cost
      FROM m GROUP BY goods_id, warehouse_id
    )
    SELECT g.id AS gid, g.code, g.name, g.spec, g.model, g.unit, g.remark, a.warehouse_id,
      a.in_qty, a.in_amt, a.in_cost, a.out_qty, a.out_amt, a.out_cost
    FROM goods g LEFT JOIN agg a ON a.goods_id = g.id
    ORDER BY g.code, g.id, a.warehouse_id
    """
    rows = conn().execute(sql, {"s": s, "e": e}).fetchall()
    wh, _, _ = _maps()
    # 进出类别/往来单位/供领人员：先找出期间内匹配的 货物+仓库 组合，再过滤汇总行
    pairs = None
    if doc_category or unit_id or person:
        csql = MOVEMENT_CTE + " SELECT DISTINCT m.goods_id, m.warehouse_id FROM m WHERE m.date>=:s AND m.date<=:e"
        cparams = {"s": s, "e": e}
        if doc_category:
            csql += " AND m.category LIKE :dc"; cparams["dc"] = f"%{doc_category}%"
        if unit_id:
            csql += " AND m.unit_id=:u"; cparams["u"] = unit_id
        if person:
            csql += " AND m.sign_a LIKE :p"; cparams["p"] = f"%{person}%"
        pairs = {(r["goods_id"], r["warehouse_id"]) for r in conn().execute(csql, cparams).fetchall()}
    SUM_KEYS = ["in_qty", "in_amt", "in_cost", "out_qty", "out_amt", "out_cost"]
    out = []
    for r in rows:
        if warehouse_id and r["warehouse_id"] != warehouse_id:
            continue
        if pairs is not None and (r["goods_id"], r["warehouse_id"]) not in pairs:
            continue
        out.append({"gid": r["gid"], "code": r["code"], "name": r["name"], "spec": r["spec"],
                    "model": r["model"], "unit": r["unit"], "remark": r["remark"] or "",
                    "warehouse": wh.get(r["warehouse_id"], "") if r["warehouse_id"] else "",
                    "in_qty": round(r["in_qty"] or 0, 2), "in_amt": round(r["in_amt"] or 0, 2),
                    "in_cost": round(r["in_cost"] or 0, 2),
                    "out_qty": round(r["out_qty"] or 0, 2), "out_amt": round(r["out_amt"] or 0, 2),
                    "out_cost": round(r["out_cost"] or 0, 2)})
    out = _flt_goods(out, goods_id, category_id, "gid")
    if by_wh == 0:
        out = _merge_rows(out, "gid", SUM_KEYS, "warehouse")
    return out


@router.get("/reports/profit")
def profit(start: str = None, end: str = None, user=Depends(get_current_user)):
    s = start or "0000-01-01"
    e = end or "9999-12-31"
    income = conn().execute(
        "SELECT COALESCE(SUM(amount),0) v FROM outbound_item i JOIN outbound h ON h.id=i.doc_id WHERE h.date>=? AND h.date<=?",
        (s, e)).fetchone()["v"]
    cost = conn().execute(
        "SELECT COALESCE(SUM(i.qty*g.purchase_price),0) v FROM outbound_item i JOIN outbound h ON h.id=i.doc_id "
        "JOIN goods g ON g.id=i.goods_id WHERE h.date>=? AND h.date<=?", (s, e)).fetchone()["v"]
    return {"income": round(income, 2), "cost": round(cost, 2), "profit": round(income - cost, 2),
            "start": start, "end": end}


@router.get("/reports/profit-goods")
def profit_goods(start: str = None, end: str = None, goods_id: int = None, category_id: int = None,
                 warehouse_id: int = None, doc_category: str = None, unit_id: int = None,
                 person: str = None, by_wh: int = 1, user=Depends(get_current_user)):
    """按货物+仓库的利润分析：出库数量 / 单据金额 / 成本(采购价) / 毛利润。"""
    wh, loc, goods = _maps()
    where, params = ["m.type='出库'"], []
    if start:
        where.append("m.date>=?"); params.append(start)
    if end:
        where.append("m.date<=?"); params.append(end)
    if goods_id:
        where.append("m.goods_id=?"); params.append(goods_id)
    if warehouse_id:
        where.append("m.warehouse_id=?"); params.append(warehouse_id)
    if doc_category:
        where.append("m.category LIKE ?"); params.append(f"%{doc_category}%")
    if unit_id:
        where.append("m.unit_id=?"); params.append(unit_id)
    if person:
        where.append("m.sign_a LIKE ?"); params.append(f"%{person}%")
    rows = conn().execute(
        MOVEMENT_CTE + f" SELECT m.goods_id, m.warehouse_id, SUM(-m.qty) qty, SUM(-m.amount) amt, SUM(-m.cost) cost "
        f"FROM m WHERE {' AND '.join(where)} GROUP BY m.goods_id, m.warehouse_id", params).fetchall()
    out = []
    for r in rows:
        g = goods.get(r["goods_id"], {})
        amt = round(r["amt"] or 0, 2); cost = round(r["cost"] or 0, 2)
        out.append({"code": g.get("code"), "name": g.get("name"), "spec": g.get("spec"),
                    "model": g.get("model"), "unit": g.get("unit"),
                    "warehouse": wh.get(r["warehouse_id"], "") if r["warehouse_id"] else "",
                    "gid": r["goods_id"],
                    "qty": round(r["qty"] or 0, 2), "amt": amt, "cost": cost,
                    "profit": round(amt - cost, 2)})
    out = _flt_goods(out, None, category_id, "gid")
    if by_wh == 0:
        out = _merge_rows(out, "gid", ["qty", "amt", "cost", "profit"], "warehouse")
    out.sort(key=lambda x: (x["code"] or "", x["warehouse"]))
    return out


@router.get("/reports/borrow-summary")
def borrow_summary(start: str = None, end: str = None, warehouse_id: int = None,
                   user=Depends(get_current_user)):
    """按货物汇总借出/归还/待还（可按日期与仓库过滤）。"""
    where, params = [], []
    if start:
        where.append("b.date>=?"); params.append(start)
    if end:
        where.append("b.date<=?"); params.append(end)
    if warehouse_id:
        where.append("l.warehouse_id=?"); params.append(warehouse_id)
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    rows = conn().execute(
        f"""SELECT g.id gid, g.code, g.name, g.spec, g.model, g.unit,
           SUM(CASE WHEN b.btype='lend' THEN b.qty ELSE 0 END) lend_qty,
           SUM(CASE WHEN b.btype='lend' THEN b.returned_qty ELSE 0 END) lend_ret
           FROM borrow b JOIN goods g ON g.id=b.goods_id LEFT JOIN locations l ON l.id=b.location_id
           {wsql}
           GROUP BY g.id ORDER BY g.code""", params).fetchall()
    out = []
    for r in rows:
        lend = r["lend_qty"] or 0
        ret = r["lend_ret"] or 0
        out.append({"code": r["code"], "name": r["name"], "spec": r["spec"], "model": r["model"],
                    "unit": r["unit"], "warehouse": "",
                    "lend_qty": lend, "lend_ret": ret, "lend_pending": round(lend - ret, 2), "lend_cost": 0,
                    "in_qty": 0, "in_ret": 0, "in_pending": 0, "in_cost": 0})
    return out


@router.get("/docs-query")
def docs_query(start: str = None, end: str = None, doc_type: str = None,
               unit: str = None, category: str = None, warehouse: str = None,
               sign_a: str = None, operator: str = None, user=Depends(get_current_user)):
    """跨类型单据联合查询（单据查询窗口数据源），支持原版查询条件窗口的全部过滤项。"""
    c = conn()
    wh = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM warehouses").fetchall()}
    unit_map = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM units").fetchall()}
    out = []
    specs = [
        ("inbound", "入库单", "inbound", "unit_id", "warehouse_id", None),
        ("outbound", "出库单", "outbound", "unit_id", "warehouse_id", None),
        ("transfer", "调拨单", "transfer", None, "from_warehouse_id", "to_warehouse_id"),
        ("check", "盘点单", "chk", None, "warehouse_id", None),
        ("initial", "期初库存", "initial", None, None, None),
    ]
    for t, label, tbl, ucol, w1, w2 in specs:
        if doc_type and t != doc_type:
            continue
        if tbl == "initial":
            hcols = "id,doc_no,date,NULL AS unit_id,NULL AS warehouse_id,NULL AS from_warehouse_id,NULL AS to_warehouse_id,NULL AS category,operator,NULL AS sign_a,NULL AS sign_b,remark"
        elif tbl == "transfer":
            hcols = "id,doc_no,date,NULL AS unit_id,from_warehouse_id,to_warehouse_id,category,operator,sign_a,sign_b,remark"
        elif tbl == "chk":
            hcols = "id,doc_no,date,NULL AS unit_id,warehouse_id,NULL AS from_warehouse_id,NULL AS to_warehouse_id,category,operator,sign_a,sign_b,remark"
        else:
            hcols = "id,doc_no,date,unit_id,warehouse_id,NULL AS from_warehouse_id,NULL AS to_warehouse_id,category,operator,sign_a,sign_b,remark"
        rows = c.execute(f"SELECT {hcols} FROM {tbl} ORDER BY id DESC").fetchall()
        for h in rows:
            if start and (h["date"] or "") < start:
                continue
            if end and (h["date"] or "") > end:
                continue
            u_name = unit_map.get(h["unit_id"], "") if h["unit_id"] else ""
            if unit and unit not in (u_name or ""):
                continue
            if category and category not in (h["category"] or ""):
                continue
            w1 = wh.get(h["warehouse_id"], "") if h["warehouse_id"] else ""
            w2 = wh.get(h["to_warehouse_id"], "") if h["to_warehouse_id"] else ""
            if warehouse and warehouse not in w1 and warehouse not in w2:
                continue
            if sign_a and sign_a not in (h["sign_a"] or ""):
                continue
            if operator and operator not in (h["operator"] or ""):
                continue
            amt = c.execute(f"SELECT COALESCE(SUM(amount),0) v FROM {tbl}_item WHERE doc_id=?", (h["id"],)).fetchone()["v"]
            out.append({
                "id": h["id"], "type": t, "type_label": label, "doc_no": h["doc_no"], "date": h["date"],
                "unit": u_name,
                "category": h["category"] or "",
                "wh1": w1, "wh2": w2,
                "amount": round(amt, 2),
                "sign_a": h["sign_a"] or "", "operator": h["operator"] or "", "sign_b": h["sign_b"] or "",
                "remark": h["remark"] or "",
            })
    out.sort(key=lambda x: x["date"] or "", reverse=True)
    return out


@router.get("/initial-items")
def initial_items(user=Depends(get_current_user)):
    """期初库存明细（按行铺开，供期初库存窗口）。"""
    c = conn()
    g = {r["id"]: dict(r) for r in c.execute("SELECT id,code,name,spec,model,unit FROM goods").fetchall()}
    wh = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM warehouses").fetchall()}
    loc = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM locations").fetchall()}
    rows = c.execute(
        """SELECT i.doc_id, h.doc_no, h.date, i.goods_id, i.warehouse_id, i.location_id,
           i.qty, i.price, i.amount, i.remark AS item_remark FROM initial_item i
           JOIN initial h ON h.id=i.doc_id ORDER BY h.id DESC, i.id""").fetchall()
    return [{"doc_id": r["doc_id"], "doc_no": r["doc_no"], "date": r["date"],
             "goods_id": r["goods_id"], "warehouse_id": r["warehouse_id"], "location_id": r["location_id"],
             "code": g.get(r["goods_id"], {}).get("code"), "name": g.get(r["goods_id"], {}).get("name"),
             "spec": g.get(r["goods_id"], {}).get("spec"), "model": g.get(r["goods_id"], {}).get("model"),
             "unit": g.get(r["goods_id"], {}).get("unit"),
             "warehouse": wh.get(r["warehouse_id"], ""), "location": loc.get(r["location_id"], ""),
             "qty": r["qty"], "price": r["price"], "amount": r["amount"],
             "remark": r["item_remark"] or ""} for r in rows]


# ---------- 报表单元格编辑 ----------
# 白名单：(表名, 字段)。只有进入白名单的字段才允许在报表中直接编辑。
EDITABLE_FIELDS = {
    ("goods", "min_stock"), ("goods", "max_stock"), ("goods", "remark"),
    ("inbound_item", "remark"), ("outbound_item", "remark"), ("transfer_item", "remark"),
    ("chk_item", "remark"), ("initial_item", "remark"),
    ("inbound", "remark"), ("outbound", "remark"), ("transfer", "remark"),
    ("chk", "remark"), ("initial", "remark"),
}
NUMERIC_FIELDS = {"min_stock", "max_stock"}


@router.put("/report-edit")
def report_edit(body: dict, user=Depends(require_perm("reports"))):
    """报表单元格保存：body = {table, field, id, value}"""
    table = (body.get("table") or "").strip()
    field = (body.get("field") or "").strip()
    rid = body.get("id")
    value = body.get("value")
    if (table, field) not in EDITABLE_FIELDS:
        raise HTTPException(400, "该字段不允许编辑")
    if not isinstance(rid, int):
        raise HTTPException(400, "参数错误")
    if field in NUMERIC_FIELDS:
        try:
            value = float(value or 0)
        except (TypeError, ValueError):
            raise HTTPException(400, "请输入数字")
    else:
        value = "" if value is None else str(value)
    cur = conn().execute(f"UPDATE {table} SET {field}=? WHERE id=?", (value, rid))
    conn().commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "记录不存在")
    log_op(user["username"], "报表编辑", f"{table}.{field}", f"id={rid} 新值: {value}")
    return {"ok": True, "value": value}
