"""Memory data models for AITuber framework."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class MemoryType(str, Enum):
    """記憶の種類"""

    SHORT_TERM = "short_term"  # 短期記憶
    LONG_TERM = "long_term"  # 長期記憶
    IMPORTANT = "important"  # 重要な記憶
    FACT = "fact"  # 事実情報


class Memory(BaseModel):
    """記憶データ"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str
    user_id: str
    text: str
    memory_type: MemoryType = MemoryType.SHORT_TERM
    importance: float = 0.5  # 重要度（0.0〜1.0）
    embedding_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """会話履歴"""

    id: str
    character_id: str
    user_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
