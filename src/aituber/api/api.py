from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import Literal, Dict, List, Optional
import yaml
import os
from contextlib import asynccontextmanager
from aituber.core.models.character import Character
from aituber.core.services.tts_service import TTSSyncService
from aituber.api.constants import CHARACTER_DIR
from aituber.app import get_app

# FastAPIのlifespanでアプリケーション初期化
tuber_app = None


@asynccontextmanager
async def lifespan(app):
    global tuber_app
    tuber_app = await get_app()
    yield


app = FastAPI(lifespan=lifespan)

# TTSサービスは同期版を利用（必要に応じて非同期版も追加可）
tts_service = TTSSyncService()

# メモリ上の会話履歴: {conversation_id: List[Dict{"role": str, "content": str}]}
conversations: Dict[str, List[Dict[str, str]]] = {}


class ChatRequest(BaseModel):
    character_id: str
    user_id: str
    conversation_id: Optional[str] = None
    message: str
    response_type: Literal["text", "audio"] = "text"


class ChatResponse(BaseModel):
    conversation_id: str
    text: Optional[str] = None


@app.post("/chat")
async def chat(req: ChatRequest):
    global tuber_app
    if tuber_app is None:
        tuber_app = await get_app()
    # キャラクターYAMLロード
    char_path = os.path.join(CHARACTER_DIR, f"{req.character_id}.yaml")
    if not os.path.exists(char_path):
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
    with open(char_path, "r", encoding="utf-8") as f:
        char_data = yaml.safe_load(f)
    character = Character(**char_data)

    # 会話サービス取得
    conversation_service = tuber_app.conversation_service
    # 会話コンテキスト取得/作成
    conversation = conversation_service.get_or_create_conversation(
        character_id=req.character_id,
        user_id=req.user_id,
        conversation_id=req.conversation_id,
    )

    # LLMで返答生成
    try:
        reply = await conversation_service.process_message(
            conversation.conversation_id, req.message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM応答生成エラー: {e}")

    if req.response_type == "text":
        return ChatResponse(conversation_id=conversation.conversation_id, text=reply)
    elif req.response_type == "audio":
        try:
            wav = tts_service.synthesize(reply, character)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS合成エラー: {e}")
        headers = {"X-Conversation-Id": conversation.conversation_id}
        return Response(content=wav, media_type="audio/wav", headers=headers)
    else:
        raise HTTPException(
            status_code=400, detail="response_typeは'text'または'audio'のみ対応"
        )
