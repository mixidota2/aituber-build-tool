#!/usr/bin/env python3
"""サーバー動作確認用スクリプト"""

import subprocess
import time
import requests
import signal
import sys
import os

def test_server():
    """サーバーをテストする"""
    
    print("=== AITuber APIサーバー動作確認 ===\n")
    
    # サーバーを起動
    print("1. サーバーを起動中...")
    server_process = subprocess.Popen(
        ["uv", "run", "aituber", "serve", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # サーバー起動を待機
    print("   サーバー起動を待機中...")
    time.sleep(10)
    
    try:
        # 1. キャラクター一覧のテスト
        print("\n2. キャラクター一覧を取得...")
        try:
            response = requests.get("http://127.0.0.1:8000/characters", timeout=5)
            if response.status_code == 200:
                characters = response.json()["characters"]
                print(f"   ✓ 成功: {len(characters)}個のキャラクターが見つかりました")
                for char in characters:
                    print(f"     - ID: {char['id']}, 名前: {char['name']}")
                
                if characters:
                    character_id = characters[0]["id"]
                    print(f"   テストに使用するキャラクター: {character_id}")
                    
                    # 2. テキスト対話のテスト
                    print("\n3. テキスト対話をテスト...")
                    chat_data = {
                        "character_id": character_id,
                        "user_id": "test_user",
                        "message": "こんにちは！テストです",
                        "response_type": "text"
                    }
                    
                    response = requests.post("http://127.0.0.1:8000/chat", json=chat_data, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        print(f"   ✓ 成功: {result['text'][:50]}...")
                        conversation_id = result["conversation_id"]
                        print(f"   会話ID: {conversation_id}")
                        
                        # 3. テキスト→音声変換のテスト
                        print("\n4. テキスト→音声変換をテスト...")
                        tts_data = {
                            "character_id": character_id,
                            "user_id": "test_user",
                            "conversation_id": conversation_id,
                            "message": "音声で返事してください"
                        }
                        
                        response = requests.post("http://127.0.0.1:8000/chat/text-to-speech", json=tts_data, timeout=15)
                        if response.status_code == 200:
                            audio_size = len(response.content)
                            print(f"   ✓ 成功: {audio_size}バイトの音声データを取得")
                            print(f"   Content-Type: {response.headers.get('content-type')}")
                            
                            # 音声ファイルを保存
                            with open("test_response.wav", "wb") as f:
                                f.write(response.content)
                            print("   音声ファイルを test_response.wav として保存")
                        else:
                            print(f"   ✗ 失敗: {response.status_code} - {response.text}")
                    else:
                        print(f"   ✗ 失敗: {response.status_code} - {response.text}")
                else:
                    print("   ⚠ キャラクターが見つかりません。'aituber init'を実行してください。")
            else:
                print(f"   ✗ 失敗: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            print("   ✗ サーバーに接続できません")
        except Exception as e:
            print(f"   ✗ エラー: {e}")
            
    finally:
        # サーバーを停止
        print("\n5. サーバーを停止中...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("   ✓ サーバーを正常に停止しました")
        except subprocess.TimeoutExpired:
            server_process.kill()
            print("   ⚠ サーバーを強制終了しました")
    
    print("\n=== テスト完了 ===")


if __name__ == "__main__":
    try:
        test_server()
    except KeyboardInterrupt:
        print("\n中断されました")
        sys.exit(1)