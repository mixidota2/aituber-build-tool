#!/usr/bin/env python3
"""
AITuber API テストスクリプト

使用方法:
1. APIサーバーを起動: aituber serve
2. このスクリプトを実行: python examples/api_test.py
"""

import requests
import json
import time

# APIサーバーのベースURL
BASE_URL = "http://127.0.0.1:8000"

def test_api_server():
    """APIサーバーのテスト"""
    
    print("=== AITuber API テスト ===\n")
    
    # 1. キャラクター一覧の取得
    print("1. キャラクター一覧を取得...")
    try:
        response = requests.get(f"{BASE_URL}/characters")
        if response.status_code == 200:
            characters = response.json()["characters"]
            print(f"✓ キャラクター数: {len(characters)}")
            for char in characters:
                print(f"  - ID: {char['id']}, 名前: {char['name']}")
        else:
            print(f"✗ エラー: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("✗ APIサーバーに接続できません。先にサーバーを起動してください:")
        print("  aituber serve")
        return
    
    if not characters:
        print("キャラクターが見つかりません。先に初期化してください:")
        print("  aituber init")
        return
    
    character_id = characters[0]["id"]
    print(f"\nテストに使用するキャラクター: {character_id}\n")
    
    # 2. テキスト対話のテスト
    print("2. テキスト対話をテスト...")
    chat_data = {
        "character_id": character_id,
        "user_id": "test_user",
        "message": "こんにちは！調子はどう？",
        "response_type": "text"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=chat_data)
    if response.status_code == 200:
        result = response.json()
        print(f"✓ 応答: {result['text'][:100]}...")
        conversation_id = result["conversation_id"]
    else:
        print(f"✗ エラー: {response.status_code} - {response.text}")
        return
    
    # 3. テキスト→音声変換のテスト
    print("\n3. テキスト→音声変換をテスト...")
    tts_data = {
        "character_id": character_id,
        "user_id": "test_user",
        "conversation_id": conversation_id,
        "message": "音声で返事してもらえる？"
    }
    
    response = requests.post(f"{BASE_URL}/chat/text-to-speech", json=tts_data)
    if response.status_code == 200:
        audio_size = len(response.content)
        print(f"✓ 音声データを取得: {audio_size} bytes")
        print(f"  Content-Type: {response.headers.get('content-type')}")
        print(f"  会話ID: {response.headers.get('x-conversation-id')}")
        
        # 音声ファイルを保存
        with open("test_output.wav", "wb") as f:
            f.write(response.content)
        print("  音声ファイルを test_output.wav として保存しました")
    else:
        print(f"✗ エラー: {response.status_code} - {response.text}")
    
    # 4. 音声応答のテスト（通常のチャットAPI）
    print("\n4. 音声応答（通常のチャットAPI）をテスト...")
    audio_chat_data = {
        "character_id": character_id,
        "user_id": "test_user",
        "conversation_id": conversation_id,
        "message": "今度は普通のチャットAPIで音声返答をテスト",
        "response_type": "audio"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=audio_chat_data)
    if response.status_code == 200:
        audio_size = len(response.content)
        print(f"✓ 音声データを取得: {audio_size} bytes")
        
        # 音声ファイルを保存
        with open("test_output2.wav", "wb") as f:
            f.write(response.content)
        print("  音声ファイルを test_output2.wav として保存しました")
    else:
        print(f"✗ エラー: {response.status_code} - {response.text}")
    
    # 5. ストリーミング対話のテスト
    print("\n5. ストリーミング対話をテスト...")
    stream_data = {
        "character_id": character_id,
        "user_id": "test_user",
        "conversation_id": conversation_id,
        "message": "ストリーミングで長めの返答をお願いします"
    }
    
    response = requests.post(f"{BASE_URL}/chat/stream", json=stream_data, stream=True)
    if response.status_code == 200:
        print("✓ ストリーミング応答:")
        print("  ", end="")
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            if chunk:
                print(chunk, end="", flush=True)
        print()
    else:
        print(f"✗ エラー: {response.status_code} - {response.text}")
    
    # 6. 会話履歴のテスト
    print("\n6. 会話履歴を取得...")
    response = requests.get(f"{BASE_URL}/conversations/{conversation_id}/history")
    if response.status_code == 200:
        history = response.json()["history"]
        print(f"✓ 会話履歴: {len(history)} 件のメッセージ")
    else:
        print(f"✗ エラー: {response.status_code} - {response.text}")
    
    print("\n=== テスト完了 ===")
    print("音声ファイルが保存されました:")
    print("- test_output.wav (テキスト→音声変換)")
    print("- test_output2.wav (音声応答チャット)")


def test_curl_examples():
    """cURLコマンドの例を表示"""
    
    print("\n=== cURLコマンドの例 ===\n")
    
    print("1. キャラクター一覧:")
    print("curl http://127.0.0.1:8000/characters\n")
    
    print("2. テキスト対話:")
    print("""curl -X POST http://127.0.0.1:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "character_id": "railly",
    "user_id": "test_user", 
    "message": "こんにちは！",
    "response_type": "text"
  }'\n""")
    
    print("3. テキスト→音声変換:")
    print("""curl -X POST http://127.0.0.1:8000/chat/text-to-speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "character_id": "railly",
    "user_id": "test_user",
    "message": "音声で返事して！"
  }' \\
  --output response.wav\n""")
    
    print("4. 音声応答（チャットAPI）:")
    print("""curl -X POST http://127.0.0.1:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "character_id": "railly",
    "user_id": "test_user",
    "message": "音声で返事してください",
    "response_type": "audio"
  }' \\
  --output chat_audio.wav\n""")


if __name__ == "__main__":
    test_api_server()
    test_curl_examples()