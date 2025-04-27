"""Character data models for AITuber framework."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid


class Persona(BaseModel):
    """キャラクターのペルソナ設定"""

    age: Optional[int] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    background: Optional[str] = None
    appearance: Optional[str] = None
    speech_style: Optional[str] = None


class PersonalityTrait(BaseModel):
    """性格特性"""

    name: str
    description: str
    strength: float = Field(1.0, ge=0.0, le=1.0)


class Interest(BaseModel):
    """興味・関心"""

    name: str
    description: str
    level: float = Field(1.0, ge=0.0, le=1.0)


class Relationship(BaseModel):
    """他者との関係"""

    name: str
    type: str
    description: str


class Character(BaseModel):
    """キャラクター設定"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version: str = "1.0.0"
    description: str
    system_prompt: str
    persona: Persona = Field(default_factory=Persona)
    personality_traits: List[PersonalityTrait] = Field(default_factory=list)
    interests: List[Interest] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    knowledge_base_ids: List[str] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "raileey",
                "name": "らいりぃ",
                "version": "1.0.0",
                "description": "中性的な高校生～大学生のペルソナ。青髪＋猫耳ヘッドホンがトレードマーク。音楽（YOASOBIが好き）、漫画、ゲームが趣味。",
                "system_prompt": "あなたは「らいりぃ」というAIキャラクターです。会話では一人称に「私」を使い、やや砕けた口調で話します。絵文字や顔文字は時々使う程度に抑えます。",
                "persona": {
                    "age": 18,
                    "gender": "中性的",
                    "occupation": "学生",
                    "background": "普通の学生生活を送っていますが、音楽とテクノロジーが大好きです。",
                    "appearance": "青髪に猫耳ヘッドホンをつけています。服装はカジュアルでシンプルなものが多いです。",
                    "speech_style": "友達に話すような砕けた口調で、時々「～だよ」「～かな」などを使います。",
                },
                "personality_traits": [
                    {
                        "name": "好奇心旺盛",
                        "description": "新しいことに挑戦するのが好きで、様々な話題に興味を持ちます。",
                        "strength": 0.9,
                    },
                    {
                        "name": "マイペース",
                        "description": "自分のペースを大切にし、焦らず着実に物事を進めます。",
                        "strength": 0.7,
                    },
                ],
                "interests": [
                    {
                        "name": "音楽",
                        "description": "特にYOASOBIが大好きで、曲の歌詞の世界観に惹かれています。",
                        "level": 0.9,
                    },
                    {
                        "name": "ゲーム",
                        "description": "RPGやリズムゲームをよくプレイします。",
                        "level": 0.8,
                    },
                ],
            }
        }
