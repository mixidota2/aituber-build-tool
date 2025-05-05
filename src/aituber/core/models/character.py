"""キャラクターモデルの定義"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class PersonalityTrait(BaseModel):
    """性格特性"""

    name: str
    description: str
    score: float = Field(ge=0.0, le=1.0)


class Interest(BaseModel):
    """興味・関心"""

    name: str
    description: str
    level: float = Field(ge=0.0, le=1.0)


class Persona(BaseModel):
    """ペルソナ情報"""

    age: Optional[int] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    background: Optional[str] = None
    appearance: Optional[str] = None
    speech_style: Optional[str] = None


class VoicevoxConfig(BaseModel):
    style_id: int = Field(..., description="Voicevoxのstyle_id")


class Character(BaseModel):
    """キャラクター定義"""

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str
    system_prompt: str
    persona: Persona
    personality_traits: List[PersonalityTrait] = Field(default_factory=list)
    interests: List[Interest] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    voicevox: Optional[VoicevoxConfig] = None

    @field_validator("id")
    def validate_id(cls, v: str) -> str:
        """IDのバリデーション"""
        if not v:
            raise ValueError("キャラクターIDは空にできません")
        return v
