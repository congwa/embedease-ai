"""订单相关 Schema"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"      # 待支付
    PAID = "paid"           # 已支付
    SHIPPED = "shipped"     # 已发货
    DELIVERED = "delivered" # 已送达
    CANCELLED = "cancelled" # 已取消
    REFUNDED = "refunded"   # 已退款


class OrderItem(BaseModel):
    """订单商品项"""
    product_id: str = Field(..., description="商品ID")
    product_name: str = Field(..., description="商品名称")
    quantity: int = Field(..., description="数量")
    unit_price: float = Field(..., description="单价")
    total_price: float = Field(..., description="小计")


class OrderCreate(BaseModel):
    """创建订单请求"""
    customer_name: str = Field(..., description="客户姓名")
    customer_email: str = Field(..., description="客户邮箱")
    customer_phone: Optional[str] = Field(None, description="客户电话")
    shipping_address: str = Field(..., description="收货地址")
    items: List[OrderItem] = Field(..., description="订单商品列表")
    notes: Optional[str] = Field(None, description="备注")


class OrderUpdate(BaseModel):
    """更新订单请求"""
    status: Optional[OrderStatus] = Field(None, description="订单状态")
    shipping_address: Optional[str] = Field(None, description="收货地址")
    notes: Optional[str] = Field(None, description="备注")


class OrderResponse(BaseModel):
    """订单响应"""
    id: str = Field(..., description="订单ID")
    customer_name: str
    customer_email: str
    customer_phone: Optional[str]
    shipping_address: str
    items: List[OrderItem]
    total_amount: float = Field(..., description="订单总金额")
    status: OrderStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """订单列表响应"""
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int


class OrderStats(BaseModel):
    """订单统计"""
    total_orders: int = Field(..., description="总订单数")
    pending_orders: int = Field(..., description="待处理订单数")
    total_revenue: float = Field(..., description="总收入")