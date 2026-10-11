"""认证：PBKDF2 口令哈希 + 带过期的签名 Token + 操作权限依赖。"""
import hashlib
import hmac
import base64
import os
import time
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer

# 签名密钥：环境变量优先；否则持久化随机密钥（放数据库同目录，重建容器不丢）
_SECRET_ENV = os.environ.get("WMS_SECRET")
_KEY_FILE = os.environ.get("WMS_SECRET_FILE") or os.path.join(
    os.path.dirname(os.environ.get("WMS_DB") or os.path.join(os.path.dirname(os.path.dirname(__file__)), "wms.db")),
    "secret.key")

if _SECRET_ENV:
    SECRET = _SECRET_ENV
else:
    SECRET = ""
    try:
        if os.path.exists(_KEY_FILE):
            with open(_KEY_FILE) as f:
                SECRET = f.read().strip()
    except Exception:
        pass
    if not SECRET:
        SECRET = os.urandom(32).hex()
        try:
            os.makedirs(os.path.dirname(_KEY_FILE) or ".", exist_ok=True)
            with open(_KEY_FILE, "w") as f:
                f.write(SECRET)
        except Exception:
            pass  # 写不进则仅内存使用（每次重启需重新登录）

TOKEN_TTL = 7 * 24 * 3600  # 登录凭证有效期 7 天

BEARER = HTTPBearer(auto_error=False)


# ---------- 口令哈希（PBKDF2-SHA256 + 随机盐；兼容旧单轮 SHA-256 并自动升级） ----------
def hash_pw(pw: str) -> str:
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 120_000)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_pw(pw: str, h: str) -> bool:
    try:
        if h.startswith("pbkdf2$"):
            _, salt, expect = h.split("$", 2)
            dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 120_000)
            return hmac.compare_digest(dk.hex(), expect)
        # 旧格式：单轮 SHA-256 hex
        return hmac.compare_digest(hashlib.sha256(pw.encode()).hexdigest(), h or "")
    except Exception:
        return False


def needs_rehash(h: str) -> bool:
    return not (h or "").startswith("pbkdf2$")


# ---------- Token（含签发时间，7 天过期） ----------
def make_token(username: str) -> str:
    raw = f"{username}.{int(time.time())}"
    sig = hmac.new(SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
    return base64.urlsafe_b64encode(f"{raw}.{sig}".encode()).decode()


def parse_token(token: str) -> str:
    try:
        data = base64.urlsafe_b64decode(token.encode()).decode()
        raw, sig = data.rsplit(".", 1)
        expect = hmac.new(SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
        if hmac.compare_digest(sig, expect):
            parts = raw.split(".")
            if len(parts) >= 2 and parts[1].isdigit():
                if time.time() - int(parts[1]) > TOKEN_TTL:
                    raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
            return parts[0]
    except HTTPException:
        raise
    except Exception:
        pass
    raise HTTPException(status_code=401, detail="无效或过期的登录凭证")


def get_current_user(cred=Depends(BEARER)):
    if cred is None or not cred.credentials:
        raise HTTPException(status_code=401, detail="未登录")
    username = parse_token(cred.credentials)
    from .db import fetchone
    row = fetchone("SELECT id,username,role,name,title,enabled,permissions FROM users WHERE username=?", (username,))
    if not row:
        raise HTTPException(status_code=401, detail="用户不存在")
    d = dict(row)
    if d.get("enabled", 1) == 0:
        raise HTTPException(status_code=403, detail="该账号已被禁用，请联系管理员")
    if d.get("title") is None:
        d["title"] = ""
    d["permissions"] = _parse_perms(d.get("permissions"))
    return d


def _parse_perms(raw):
    """permissions 列存 JSON 数组；管理员拥有全部权限。"""
    import json
    if not raw:
        return []
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except Exception:
        return []


def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def require_perm(key: str):
    """按权限键校验（原版"账号权限"）：管理员全放行，普通用户须勾选对应权限。"""
    def dep(user=Depends(get_current_user)):
        if user["role"] == "admin" or key in (user.get("permissions") or []):
            return user
        raise HTTPException(status_code=403, detail="没有此操作权限，请联系管理员在【账号权限】中勾选")
    return dep


# ---------- 登录限速（防口令爆破；内存计数，同用户名 5 次失败锁 5 分钟） ----------
_login_fail = {}

def login_too_many(username: str) -> bool:
    rec = _login_fail.get(username)
    return bool(rec and rec[0] >= 5 and time.time() - rec[1] < 300)

def login_fail(username: str):
    rec = _login_fail.setdefault(username, [0, time.time()])
    if time.time() - rec[1] > 300:
        rec[0] = 0
    rec[0] += 1
    rec[1] = time.time()

def login_ok(username: str):
    _login_fail.pop(username, None)
