#!/usr/bin/env python3
"""サーバー起動デバッグ用スクリプト"""

import subprocess
import time

def debug_server():
    """サーバー起動をデバッグする"""
    
    print("=== サーバー起動デバッグ ===\n")
    
    # サーバーを起動（出力を表示）
    print("サーバーを起動中...")
    try:
        process = subprocess.run(
            ["uv", "run", "aituber", "serve", "--host", "127.0.0.1", "--port", "8000"],
            timeout=15,
            capture_output=True,
            text=True
        )
        
        print("STDOUT:")
        print(process.stdout)
        print("\nSTDERR:")
        print(process.stderr)
        print(f"\nReturn code: {process.returncode}")
        
    except subprocess.TimeoutExpired as e:
        print("タイムアウトしました")
        print("STDOUT:")
        print(e.stdout if e.stdout else "なし")
        print("\nSTDERR:")
        print(e.stderr if e.stderr else "なし")

if __name__ == "__main__":
    debug_server()