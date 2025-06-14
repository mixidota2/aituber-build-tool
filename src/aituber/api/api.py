from fastapi import FastAPI, HTTPException, Response, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Dict, List, Optional, AsyncGenerator
import yaml
import os
import json
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
    response_type: Literal["text", "audio", "both"] = "text"
    stream: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    text: Optional[str] = None
    audio_url: Optional[str] = None


class StreamChatRequest(BaseModel):
    character_id: str
    user_id: str
    conversation_id: Optional[str] = None
    message: str


class VoiceChatRequest(BaseModel):
    character_id: str
    user_id: str
    conversation_id: Optional[str] = None


class CharacterListResponse(BaseModel):
    characters: List[Dict[str, str]]


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    history: List[Dict[str, str]]


class TextToSpeechRequest(BaseModel):
    character_id: str
    user_id: str
    conversation_id: Optional[str] = None
    message: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    global tuber_app
    if tuber_app is None:
        tuber_app = await get_app()
    
    # キャラクター取得
    character = await get_character(req.character_id)
    
    # 会話サービス取得
    conversation_service = tuber_app.conversation_service
    
    # 会話コンテキスト取得/作成
    conversation = conversation_service.get_or_create_conversation(
        character_id=req.character_id,
        user_id=req.user_id,
        conversation_id=req.conversation_id,
    )

    # ストリーミング対応
    if req.stream:
        return StreamingResponse(
            stream_chat_response(conversation_service, conversation.conversation_id, req.message, character, req.response_type),
            media_type="text/plain" if req.response_type == "text" else "application/json"
        )

    # 通常のレスポンス
    try:
        reply = await conversation_service.process_message(
            conversation.conversation_id, req.message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM応答生成エラー: {e}")

    response = ChatResponse(conversation_id=conversation.conversation_id)
    
    if req.response_type in ["text", "both"]:
        response.text = reply
    
    if req.response_type == "audio":
        try:
            wav = tts_service.synthesize(reply, character)
            headers = {"X-Conversation-Id": conversation.conversation_id}
            return Response(content=wav, media_type="audio/wav", headers=headers)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS合成エラー: {e}")
    elif req.response_type == "both":
        try:
            wav = tts_service.synthesize(reply, character)
            response.audio_url = f"/audio/{conversation.conversation_id}/latest"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS合成エラー: {e}")

    return response


@app.post("/chat/stream")
async def stream_chat(req: StreamChatRequest):
    global tuber_app
    if tuber_app is None:
        tuber_app = await get_app()
    
    _ = await get_character(req.character_id)  # キャラクター存在確認
    conversation_service = tuber_app.conversation_service
    
    conversation = conversation_service.get_or_create_conversation(
        character_id=req.character_id,
        user_id=req.user_id,
        conversation_id=req.conversation_id,
    )

    return StreamingResponse(
        stream_text_response(conversation_service, conversation.conversation_id, req.message),
        media_type="text/plain"
    )


@app.post("/chat/voice")
async def voice_chat(
    audio: UploadFile = File(...),
    character_id: str = "railly",
    user_id: str = "default",
    conversation_id: Optional[str] = None
):
    global tuber_app
    if tuber_app is None:
        tuber_app = await get_app()
    
    # 音声ファイルの処理（今回は簡略化）
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="音声ファイルを送信してください")
    
    # 音声をテキストに変換（実装は省略、プレースホルダー）
    transcribed_text = "こんにちは"  # 実際にはSTTサービスを使用
    
    character = await get_character(character_id)
    conversation_service = tuber_app.conversation_service
    
    conversation = conversation_service.get_or_create_conversation(
        character_id=character_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    try:
        reply = await conversation_service.process_message(
            conversation.conversation_id, transcribed_text
        )
        wav = tts_service.synthesize(reply, character)
        headers = {"X-Conversation-Id": conversation.conversation_id}
        return Response(content=wav, media_type="audio/wav", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声対話エラー: {e}")


@app.get("/characters", response_model=CharacterListResponse)
async def list_characters():
    characters = []
    if os.path.exists(CHARACTER_DIR):
        for filename in os.listdir(CHARACTER_DIR):
            if filename.endswith(".yaml"):
                char_id = filename[:-5]  # .yamlを除く
                char_path = os.path.join(CHARACTER_DIR, filename)
                try:
                    with open(char_path, "r", encoding="utf-8") as f:
                        char_data = yaml.safe_load(f)
                    characters.append({
                        "id": char_id,
                        "name": char_data.get("name", char_id),
                        "description": char_data.get("persona", "")[:100] + "..."
                    })
                except Exception:
                    continue
    return CharacterListResponse(characters=characters)


@app.get("/conversations/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str):
    history = conversations.get(conversation_id, [])
    return ConversationHistoryResponse(conversation_id=conversation_id, history=history)


@app.post("/chat/text-to-speech")
async def text_to_speech_chat(req: TextToSpeechRequest):
    """テキスト入力でAIが音声で返答するエンドポイント"""
    global tuber_app
    if tuber_app is None:
        tuber_app = await get_app()
    
    character = await get_character(req.character_id)
    conversation_service = tuber_app.conversation_service
    
    conversation = conversation_service.get_or_create_conversation(
        character_id=req.character_id,
        user_id=req.user_id,
        conversation_id=req.conversation_id,
    )

    try:
        reply = await conversation_service.process_message(
            conversation.conversation_id, req.message
        )
        wav = tts_service.synthesize(reply, character)
        headers = {
            "X-Conversation-Id": conversation.conversation_id,
            "X-Response-Length": str(len(reply))
        }
        return Response(content=wav, media_type="audio/wav", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"テキスト→音声変換エラー: {e}")


async def get_character(character_id: str) -> Character:
    char_path = os.path.join(CHARACTER_DIR, f"{character_id}.yaml")
    if not os.path.exists(char_path):
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
    with open(char_path, "r", encoding="utf-8") as f:
        char_data = yaml.safe_load(f)
    return Character(**char_data)


async def stream_text_response(conversation_service, conversation_id: str, message: str) -> AsyncGenerator[str, None]:
    try:
        async for chunk in conversation_service.process_message_stream(conversation_id, message):
            yield f"data: {json.dumps({'text': chunk, 'type': 'text'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"


async def stream_chat_response(conversation_service, conversation_id: str, message: str, character: Character, response_type: str) -> AsyncGenerator[str, None]:
    try:
        full_text = ""
        async for chunk in conversation_service.process_message_stream(conversation_id, message):
            full_text += chunk
            if response_type == "text":
                yield chunk
            else:
                yield f"data: {json.dumps({'text': chunk, 'type': 'text'})}\n\n"
        
        if response_type in ["audio", "both"]:
            try:
                _ = tts_service.synthesize(full_text, character)
                yield f"data: {json.dumps({'audio': 'generated', 'type': 'audio'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': f'TTS合成エラー: {e}', 'type': 'error'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
