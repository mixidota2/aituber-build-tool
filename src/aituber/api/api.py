from fastapi import FastAPI, HTTPException, Response, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Dict, List, Optional, AsyncGenerator
import os
import json
from contextlib import asynccontextmanager
from aituber.core.models.character import Character
from aituber.core.app_factory import AppFactory
from aituber.core.character_utils import get_character_safe, list_characters_safe

# FastAPIのlifespanでアプリケーション初期化
tuber_app = None


@asynccontextmanager
async def lifespan(app):
    global tuber_app
    tuber_app = await AppFactory.get_app()
    yield


app = FastAPI(lifespan=lifespan)

# 注意: 会話履歴は ConversationService で管理されます


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
        tuber_app = await AppFactory.get_app()
    
    # キャラクター取得
    try:
        character = await get_character_safe(tuber_app, req.character_id)
    except Exception:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
    
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
            wav = tuber_app.tts_service.synthesize(reply, character)
            headers = {"X-Conversation-Id": conversation.conversation_id}
            return Response(content=wav, media_type="audio/wav", headers=headers)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS合成エラー: {e}")
    elif req.response_type == "both":
        try:
            wav = tuber_app.tts_service.synthesize(reply, character)
            response.audio_url = f"/audio/{conversation.conversation_id}/latest"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS合成エラー: {e}")

    return response


@app.post("/chat/stream")
async def stream_chat(req: StreamChatRequest):
    global tuber_app
    if tuber_app is None:
        tuber_app = await AppFactory.get_app()
    
    try:
        _ = await get_character_safe(tuber_app, req.character_id)  # キャラクター存在確認
    except Exception:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
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
        tuber_app = await AppFactory.get_app()
    
    # 音声ファイルの処理（今回は簡略化）
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="音声ファイルを送信してください")
    
    # 音声をテキストに変換（実装は省略、プレースホルダー）
    transcribed_text = "こんにちは"  # 実際にはSTTサービスを使用
    
    try:
        character = await get_character_safe(tuber_app, character_id)
    except Exception:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
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
        wav = tuber_app.tts_service.synthesize(reply, character)
        headers = {"X-Conversation-Id": conversation.conversation_id}
        return Response(content=wav, media_type="audio/wav", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声対話エラー: {e}")


@app.get("/characters", response_model=CharacterListResponse)
async def list_characters():
    global tuber_app
    if tuber_app is None:
        tuber_app = await AppFactory.get_app()
    
    characters = await list_characters_safe(tuber_app)
    return CharacterListResponse(characters=characters)


@app.get("/conversations/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str):
    global tuber_app
    if tuber_app is None:
        tuber_app = await AppFactory.get_app()
    
    conversation_service = tuber_app.conversation_service
    context = conversation_service.get_conversation(conversation_id)
    
    if context is None:
        raise HTTPException(status_code=404, detail="会話が見つかりません")
    
    # ConversationContext.messages を API レスポンス形式に変換
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in context.messages
    ]
    
    return ConversationHistoryResponse(conversation_id=conversation_id, history=history)


@app.get("/debug/character-dir")
async def debug_character_dir():
    """デバッグ用: キャラクターディレクトリ情報を取得"""
    global tuber_app
    if tuber_app is None:
        tuber_app = await AppFactory.get_app()
    
    from aituber.core.character_utils import CharacterUtils
    character_dir = CharacterUtils.get_character_dir(tuber_app)
    return {
        "character_dir": character_dir,
        "exists": os.path.exists(character_dir),
        "files": os.listdir(character_dir) if os.path.exists(character_dir) else [],
        "cwd": os.getcwd()
    }


@app.post("/chat/text-to-speech")
async def text_to_speech_chat(req: TextToSpeechRequest):
    """テキスト入力でAIが音声で返答するエンドポイント"""
    global tuber_app
    if tuber_app is None:
        tuber_app = await AppFactory.get_app()
    
    try:
        character = await get_character_safe(tuber_app, req.character_id)
    except Exception:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
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
        wav = tuber_app.tts_service.synthesize(reply, character)
        headers = {
            "X-Conversation-Id": conversation.conversation_id,
            "X-Response-Length": str(len(reply))
        }
        return Response(content=wav, media_type="audio/wav", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"テキスト→音声変換エラー: {e}")


# 古いユーティリティ関数は削除され、character_utilsに移行されました


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
                if tuber_app is not None:
                    _ = tuber_app.tts_service.synthesize(full_text, character)
                yield f"data: {json.dumps({'audio': 'generated', 'type': 'audio'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': f'TTS合成エラー: {e}', 'type': 'error'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
