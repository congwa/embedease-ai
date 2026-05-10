"""管理后台 — 订单 API"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.models.order import Order
from app.schemas.admin import PaginatedResponse
from app.schemas.order import OrderCreate, OrderItem, OrderResponse, OrderStatus, OrderUpdate

router = APIRouter(prefix="/api/v1/admin/orders", tags=["admin-orders"])


def _order_to_response(row: Order) -> OrderResponse:
    raw = json.loads(row.items_json or "[]")
    items = [OrderItem.model_validate(x) for x in raw]
    return OrderResponse(
        id=row.id,
        customer_name=row.customer_name,
        customer_email=row.customer_email,
        customer_phone=row.customer_phone,
        shipping_address=row.shipping_address,
        items=items,
        total_amount=row.total_amount,
        status=OrderStatus(row.status),
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _compute_total(items: list[OrderItem]) -> float:
    return float(sum(i.total_price for i in items))


@router.get("", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    db: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: OrderStatus | None = Query(None, alias="status"),
    customer_email: str | None = None,
):
    """分页查询订单"""
    query = select(Order)

    if status_filter is not None:
        query = query.where(Order.status == status_filter.value)
    if customer_email:
        query = query.where(Order.customer_email.ilike(f"%{customer_email}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.order_by(Order.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.scalars().all()

    return PaginatedResponse(
        items=[_order_to_response(r) for r in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=((total or 0) + page_size - 1) // page_size,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取单个订单"""
    row = await db.get(Order, order_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return _order_to_response(row)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """创建订单"""
    if not body.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订单商品列表不能为空")

    computed = _compute_total(body.items)
    oid = str(uuid.uuid4())
    order = Order(
        id=oid,
        customer_name=body.customer_name,
        customer_email=body.customer_email,
        customer_phone=body.customer_phone,
        shipping_address=body.shipping_address,
        items_json=json.dumps([i.model_dump() for i in body.items], ensure_ascii=False),
        total_amount=computed,
        status=OrderStatus.PENDING.value,
        notes=body.notes,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return _order_to_response(order)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    body: OrderUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """修改订单（部分字段）"""
    row = await db.get(Order, order_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")

    if body.status is not None:
        row.status = body.status.value
    if body.shipping_address is not None:
        row.shipping_address = body.shipping_address
    if body.notes is not None:
        row.notes = body.notes

    await db.flush()
    await db.refresh(row)
    return _order_to_response(row)
