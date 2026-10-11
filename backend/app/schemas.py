"""Pydantic 模型定义。"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any


class LoginReq(BaseModel):
    username: str
    password: str


class ChangePwdReq(BaseModel):
    old_password: str
    new_password: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"
    name: Optional[str] = None
    title: Optional[str] = None
    enabled: bool = True
    remark: Optional[str] = None
    permissions: Optional[List[str]] = None   # 操作权限键列表


class UserUpdate(BaseModel):
    role: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    enabled: Optional[bool] = None
    remark: Optional[str] = None
    password: Optional[str] = None
    permissions: Optional[List[str]] = None   # 操作权限键列表


class ProfileUpdate(BaseModel):
    """个人设置：名称/职务 + 可选改密。"""
    name: Optional[str] = None
    title: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None


# 单据行项目通用结构
class DocItem(BaseModel):
    goods_id: int
    location_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    qty: float = 0
    price: float = 0
    amount: float = 0
    remark: Optional[str] = None
    # 盘点专用
    book_qty: Optional[float] = None
    actual_qty: Optional[float] = None


class DocCreate(BaseModel):
    date: Optional[str] = None
    unit_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    from_warehouse_id: Optional[int] = None
    to_warehouse_id: Optional[int] = None
    operator: Optional[str] = None
    remark: Optional[str] = None
    category: Optional[str] = None   # 进出类别
    sign_a: Optional[str] = None     # 供货人/领货人/调拨人/盘点人
    sign_b: Optional[str] = None     # 审核人
    items: List[DocItem] = []


class BorrowCreate(BaseModel):
    date: Optional[str] = None
    goods_id: int
    location_id: Optional[int] = None
    qty: float = 0
    borrower: Optional[str] = None
    btype: str = "lend"  # lend | return
    related_id: Optional[int] = None
    remark: Optional[str] = None
