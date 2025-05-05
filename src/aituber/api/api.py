from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import Literal, Dict, List, Optional
import yaml
import os
import uuid
from aituber.core.models.character import Character
from aituber.core.services.tts_service import TTSSyncService
from aituber.api.constants import CHARACTER_DIR

app = FastAPI()

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
def chat(req: ChatRequest):
    # キャラクターYAMLロード
    char_path = os.path.join(CHARACTER_DIR, f"{req.character_id}.yaml")
    if not os.path.exists(char_path):
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
    with open(char_path, "r", encoding="utf-8") as f:
        char_data = yaml.safe_load(f)
    character = Character(**char_data)

    # 会話IDの決定
    if not req.conversation_id or req.conversation_id == "new":
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = []
    else:
        conversation_id = req.conversation_id
        if conversation_id not in conversations:
            conversations[conversation_id] = []

    # 履歴にユーザー発話を追加
    conversations[conversation_id].append({"role": "user", "content": req.message})

    # 返答生成（ここではダミー返答。実際はLLMやチャットAPIを呼ぶ）
    reply = f"（ダミー返答）{character.name}：{req.message} ですね。"
    conversations[conversation_id].append({"role": "assistant", "content": reply})

    if req.response_type == "text":
        return ChatResponse(conversation_id=conversation_id, text=reply)
    elif req.response_type == "audio":
        try:
            wav = tts_service.synthesize(reply, character)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS合成エラー: {e}")
        headers = {"X-Conversation-Id": conversation_id}
        return Response(content=wav, media_type="audio/wav", headers=headers)
    else:
        raise HTTPException(status_code=400, detail="response_typeは'text'または'audio'のみ対応") 