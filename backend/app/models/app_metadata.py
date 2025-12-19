"""应用元数据模型 - KV 存储（用于商品库画像等配置）"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AppMetadata(Base):
    """应用元数据表（KV 存储）
    
    用于存储：
    - catalog_profile.stats: 画像统计 JSON
    - catalog_profile.prompt_short: <=100 字的短提示词
    - catalog_profile.fingerprint: 画像指纹（用于判断变化）
    """

    __tablename__ = "app_metadata"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
