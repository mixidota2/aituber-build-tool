#!/usr/bin/env python3
"""簡単なAPIテスト"""

import requests
import json

def test_api():
    """APIをテストする（サーバーが起動していることを前提）"""
    base_url = "http://127.0.0.1:8000"
    
    print("=== 簡単なAPIテスト ===\n")
    
    try:
        # デバッグエンドポイントをテスト
        print("1. デバッグ情報を取得...")
        response = requests.get(f"{base_url}/debug/character-dir", timeout=5)
        if response.status_code == 200:
            debug_info = response.json()
            print(f"   キャラクターディレクトリ: {debug_info['character_dir']}")
            print(f"   ディレクトリ存在: {debug_info['exists']}")
            print(f"   ファイル一覧: {debug_info['files']}")
            print(f"   現在のディレクトリ: {debug_info['cwd']}")
        else:
            print(f"   エラー: {response.status_code}")
            
        # キャラクター一覧をテスト
        print("\n2. キャラクター一覧を取得...")
        response = requests.get(f"{base_url}/characters", timeout=5)
        if response.status_code == 200:
            characters = response.json()["characters"]
            print(f"   見つかったキャラクター: {len(characters)}個")
            for char in characters:
                print(f"     - {char['id']}: {char['name']}")
        else:
            print(f"   エラー: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("サーバーに接続できません。先に以下を実行してください:")
        print("  uv run aituber serve")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    test_api()