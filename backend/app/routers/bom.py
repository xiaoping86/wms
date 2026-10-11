"""BOM（物料清单）管理与产品查询。

- boms / bom_items 两张表：BOM 头字段与明细列均可自定义（field_defs/col_defs 存 JSON 定义，
  自定义值存 extra JSON）；默认表头=型号/名称/电压/电流/编号/备注，默认列=数量/图号/名称/基型/备注。
- 产品查询：选 BOM × 生产数量，逐条对比当前库存（期初+入库-出库+盘点差异），给出缺口与是否可生产。
明细与货物匹配规则：图号→货物编码精确匹配；否则名称精确匹配；再否则名称包含匹配。
"""
import json
from fastapi import APIRouter, HTTPException, Depends
from ..db import conn, WRITE_LOCK, log_op
from ..deps import get_current_user, require_perm

router = APIRouter(prefix="/api", tags=["bom"])

# 表头字段定义（model 固定为必填的型号列，其余映射到固定列，超出部分进 extra）
_DEF_HEAD = [
    {"key": "model", "label": "型号"},
    {"key": "name", "label": "名称"},
    {"key": "voltage", "label": "电压"},
    {"key": "current", "label": "电流"},
    {"key": "doc_no", "label": "编号"},
    {"key": "remark", "label": "备注"},
]
# 明细列定义（qty/dwg/name/base/remark 映射到固定列，其余进 bom_items.extra）
_DEF_COLS = [
    {"key": "qty", "label": "数量"},
    {"key": "dwg", "label": "图号"},
    {"key": "name", "label": "名称"},
    {"key": "base", "label": "基型"},
    {"key": "remark", "label": "备注"},
]
_HEAD_COLS = {"model", "name", "voltage", "current", "doc_no", "remark"}
_ITEM_COLS = {"qty", "dwg", "name", "base", "remark"}


def _clean(v):
    return (str(v).strip() if v is not None else "")


def _defs(v, dflt):
    """解析字段/列定义 JSON；非法或缺省时回退默认定义。"""
    try:
        arr = json.loads(v) if v else None
        if isinstance(arr, list) and arr and all(
                isinstance(x, dict) and x.get("key") and x.get("label") for x in arr):
            return [{"key": str(x["key"])[:30], "label": str(x["label"])[:30]} for x in arr[:20]]
    except Exception:
        pass
    return [dict(x) for x in dflt]


def _jdict(v):
    try:
        d = json.loads(v) if v else {}
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _head_of(row):
    """把 boms 行拆成 values（固定列+自定义合并展示）与 defs。"""
    head_defs = _defs(row["field_defs"], _DEF_HEAD)
    extra = _jdict(row["extra"])
    values = {"model": row["model"], "name": row["name"], "voltage": row["voltage"],
              "current": row["current"], "doc_no": row["doc_no"], "remark": row["remark"]}
    for k, v in extra.items():
        values.setdefault(k, v)
    return head_defs, values


def _items_of(bid, col_defs=None):
    rows = [dict(r) for r in conn().execute(
        "SELECT * FROM bom_items WHERE bom_id=? ORDER BY COALESCE(seq,9999), id", (bid,)).fetchall()]
    for r in rows:
        ex = _jdict(r.pop("extra", None))
        for k, v in ex.items():
            r.setdefault(k, v)
    return rows


@router.get("/boms")
def bom_list(q: str = None, user=Depends(get_current_user)):
    rows = [dict(r) for r in conn().execute("SELECT * FROM boms ORDER BY id DESC").fetchall()]
    cnt = {r["bom_id"]: r["n"] for r in conn().execute(
        "SELECT bom_id, COUNT(*) n FROM bom_items GROUP BY bom_id").fetchall()}
    out = []
    for b in rows:
        b["part_count"] = cnt.get(b["id"], 0)
        b["field_defs"], values = _head_of(b)
        b["col_defs"] = _defs(b["col_defs"], _DEF_COLS)
        b["values"] = values
        b.pop("extra", None)
        out.append(b)
    if q:
        k = q.strip().lower()
        rows = [b for b in out if k in (b["values"].get("model") or "").lower()
                or k in (b["values"].get("name") or "").lower()]
        return rows
    return out


@router.get("/boms/{bid}")
def bom_detail(bid: int, user=Depends(get_current_user)):
    b = conn().execute("SELECT * FROM boms WHERE id=?", (bid,)).fetchone()
    if not b:
        raise HTTPException(404, "BOM 不存在或已被删除")
    b = dict(b)
    head_defs, values = _head_of(b)
    col_defs = _defs(b["col_defs"], _DEF_COLS)
    return {"id": b["id"], "field_defs": head_defs, "col_defs": col_defs,
            "values": values, "items": _items_of(bid, col_defs)}


def _save_items(c, bid, items, col_defs):
    custom = [d["key"] for d in col_defs if d["key"] not in _ITEM_COLS]
    for i, it in enumerate(items, 1):
        if not _clean(it.get("name")) and not _clean(it.get("dwg")):
            continue
        ex = json.dumps({k: _clean(it.get(k)) for k in custom}, ensure_ascii=False) if custom else None
        c.execute(
            "INSERT INTO bom_items(bom_id,seq,qty,dwg,name,base,remark,extra) VALUES(?,?,?,?,?,?,?,?)",
            (bid, _clean(it.get("seq")) or i,
             float(it.get("qty") or 1), _clean(it.get("dwg")),
             _clean(it.get("name")), _clean(it.get("base")), _clean(it.get("remark")), ex))


@router.post("/boms", dependencies=[Depends(require_perm("goods"))])
def bom_create(body: dict, user=Depends(get_current_user)):
    values = body.get("values") if isinstance(body.get("values"), dict) else body
    model = _clean(values.get("model"))
    if not model:
        raise HTTPException(400, "请填写 BOM 型号")
    head_defs = _defs(json.dumps(body.get("field_defs"), ensure_ascii=False)
                      if body.get("field_defs") else None, _DEF_HEAD)
    col_defs = _defs(json.dumps(body.get("col_defs"), ensure_ascii=False)
                     if body.get("col_defs") else None, _DEF_COLS)
    items = body.get("items") or []
    c = conn()
    with WRITE_LOCK:
        try:
            head = {k: _clean(values.get(k)) for k in _HEAD_COLS if k != "model"}
            custom_head = {d["key"]: _clean(values.get(d["key"]))
                           for d in head_defs if d["key"] not in _HEAD_COLS}
            cur = c.execute(
                "INSERT INTO boms(model,name,voltage,current,doc_no,remark,field_defs,col_defs,extra)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (model, head["name"], head["voltage"], head["current"], head["doc_no"], head["remark"],
                 json.dumps(head_defs, ensure_ascii=False),
                 json.dumps(col_defs, ensure_ascii=False),
                 json.dumps(custom_head, ensure_ascii=False) if custom_head else None))
            bid = cur.lastrowid
            _save_items(c, bid, items, col_defs)
            c.commit()
        except Exception:
            c.rollback()
            raise HTTPException(400, "保存失败：型号可能已存在或数据有误")
    log_op(user["username"], "货物资料", "新建BOM", f"{model} {len(items)}项")
    return {"id": bid}


@router.put("/boms/{bid}", dependencies=[Depends(require_perm("goods"))])
def bom_update(bid: int, body: dict, user=Depends(get_current_user)):
    values = body.get("values") if isinstance(body.get("values"), dict) else body
    model = _clean(values.get("model"))
    if not model:
        raise HTTPException(400, "请填写 BOM 型号")
    head_defs = _defs(json.dumps(body.get("field_defs"), ensure_ascii=False)
                      if body.get("field_defs") else None, _DEF_HEAD)
    col_defs = _defs(json.dumps(body.get("col_defs"), ensure_ascii=False)
                     if body.get("col_defs") else None, _DEF_COLS)
    items = body.get("items") or []
    c = conn()
    with WRITE_LOCK:
        if not c.execute("SELECT id FROM boms WHERE id=?", (bid,)).fetchone():
            raise HTTPException(404, "BOM 不存在或已被删除")
        try:
            head = {k: _clean(values.get(k)) for k in _HEAD_COLS if k != "model"}
            custom_head = {d["key"]: _clean(values.get(d["key"]))
                           for d in head_defs if d["key"] not in _HEAD_COLS}
            c.execute(
                "UPDATE boms SET model=?,name=?,voltage=?,current=?,doc_no=?,remark=?,"
                "field_defs=?,col_defs=?,extra=? WHERE id=?",
                (model, head["name"], head["voltage"], head["current"], head["doc_no"], head["remark"],
                 json.dumps(head_defs, ensure_ascii=False),
                 json.dumps(col_defs, ensure_ascii=False),
                 json.dumps(custom_head, ensure_ascii=False) if custom_head else None, bid))
            c.execute("DELETE FROM bom_items WHERE bom_id=?", (bid,))
            _save_items(c, bid, items, col_defs)
            c.commit()
        except Exception:
            c.rollback()
            raise HTTPException(400, "保存失败：数据有误")
    log_op(user["username"], "货物资料", "编辑BOM", f"{model} {len(items)}项")
    return {"ok": True}


@router.delete("/boms/{bid}", dependencies=[Depends(require_perm("goods"))])
def bom_delete(bid: int, user=Depends(get_current_user)):
    c = conn()
    with WRITE_LOCK:
        b = c.execute("SELECT model FROM boms WHERE id=?", (bid,)).fetchone()
        if not b:
            raise HTTPException(404, "BOM 不存在或已被删除")
        c.execute("DELETE FROM bom_items WHERE bom_id=?", (bid,))
        c.execute("DELETE FROM boms WHERE id=?", (bid,))
        c.commit()
    log_op(user["username"], "货物资料", "删除BOM", b["model"])
    return {"ok": True}


@router.get("/boms/{bid}/check")
def bom_check(bid: int, qty: float = 1, user=Depends(get_current_user)):
    """产品查询：生产 qty 台时，逐条明细对比当前库存是否足够。"""
    if qty <= 0:
        raise HTTPException(400, "生产数量必须大于 0")
    b = conn().execute("SELECT * FROM boms WHERE id=?", (bid,)).fetchone()
    if not b:
        raise HTTPException(404, "BOM 不存在或已被删除")
    b = dict(b)
    col_defs = _defs(b["col_defs"], _DEF_COLS)
    head_defs, values = _head_of(b)
    items = _items_of(bid, col_defs)
    # 当前总库存（调拨一进一出总量不变，不计入）
    stock_rows = conn().execute("""
        SELECT goods_id, SUM(q) q FROM (
          SELECT i.goods_id, SUM(i.qty) q FROM initial_item i GROUP BY i.goods_id
          UNION ALL SELECT goods_id, SUM(qty) FROM inbound_item GROUP BY goods_id
          UNION ALL SELECT goods_id, -SUM(qty) FROM outbound_item GROUP BY goods_id
          UNION ALL SELECT goods_id, SUM(diff_qty) FROM chk_item GROUP BY goods_id
        ) GROUP BY goods_id
    """).fetchall()
    stock = {r["goods_id"]: round(r["q"] or 0, 2) for r in stock_rows}
    goods = [dict(r) for r in conn().execute("SELECT id,code,name,unit FROM goods").fetchall()]
    by_code = {g["code"]: g for g in goods if g["code"]}
    by_name = {}
    for g in goods:
        by_name.setdefault(g["name"], g)

    rows, short, unmatched = [], 0, 0
    for it in items:
        need = round(float(it.get("qty") or 0) * qty, 2)
        g = by_code.get(_clean(it.get("dwg"))) or by_name.get(_clean(it.get("name")))
        if not g and _clean(it.get("name")):
            cand = [x for x in goods if _clean(it.get("name")) in (x["name"] or "")]
            g = cand[0] if len(cand) == 1 else None
        have = round(stock.get(g["id"], 0), 2) if g else None
        gap = round(need - have, 2) if g else None
        ok = (g is not None and have >= need)
        if not ok:
            short += 1
            if not g:
                unmatched += 1
        row = {d["key"]: it.get(d["key"]) for d in col_defs}
        row.update({
            "seq": it.get("seq"), "dwg": it.get("dwg"), "name": it.get("name"),
            "base": it.get("base"), "remark": it.get("remark"),
            "per": it.get("qty"), "need": need,
            "goods_code": g["code"] if g else "", "goods_name": g["name"] if g else "",
            "unit": g["unit"] if g else "", "stock": have, "gap": gap, "ok": ok,
        })
        rows.append(row)
    return {
        "bom": {"id": b["id"], "model": values.get("model"), "name": values.get("name"),
                "values": values, "field_defs": head_defs, "col_defs": col_defs},
        "plan_qty": qty, "rows": rows,
        "summary": {"parts": len(rows), "short": short, "unmatched": unmatched,
                    "enough": short == 0},
    }
