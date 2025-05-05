"""ローカルファイルシステムを使用したストレージサービスの実装"""

import os
import json
import shutil
from typing import List, Dict, Any, Optional, BinaryIO, cast
from pathlib import Path
from datetime import datetime

from ....core.config import AITuberConfig
from .base import BaseStorageService


class LocalStorageService(BaseStorageService):
    """ローカルファイルシステムを使用したストレージサービス"""

    def __init__(self, config: AITuberConfig):
        """初期化

        Args:
            config: アプリケーション設定
        """
        self.config = config
        self.base_path = self.config.storage.local_path
        self.metadata_path = self.base_path / ".metadata"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """必要なディレクトリを作成する"""
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(self.metadata_path, exist_ok=True)

    def _get_metadata_path(self, file_path: Path) -> Path:
        """メタデータファイルのパスを取得する"""
        relative_path = file_path.relative_to(self.base_path)
        return self.metadata_path / f"{relative_path}.meta.json"

    def _ensure_metadata_directory(self, metadata_path: Path) -> None:
        """メタデータファイルのディレクトリを作成する"""
        os.makedirs(metadata_path.parent, exist_ok=True)

    async def save_file(
        self,
        file_path: Path,
        content: bytes | str | BinaryIO,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """ファイルを保存する"""
        # 絶対パスの解決
        abs_path = self.base_path / file_path
        os.makedirs(abs_path.parent, exist_ok=True)

        # ファイルの保存
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"

        if isinstance(content, (bytes, str)):
            with open(abs_path, mode=mode, encoding=encoding) as f:
                f.write(content)
        else:
            with open(abs_path, "wb") as f:
                shutil.copyfileobj(content, f)

        # メタデータの保存
        if metadata is not None:
            metadata_path = self._get_metadata_path(file_path)
            self._ensure_metadata_directory(metadata_path)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        **metadata,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        return str(abs_path)

    async def get_file(self, file_path: Path) -> bytes:
        """ファイルを取得する"""
        abs_path = self.base_path / file_path
        if not abs_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        with open(abs_path, "rb") as f:
            return f.read()

    async def delete_file(self, file_path: Path) -> bool:
        """ファイルを削除する"""
        abs_path = self.base_path / file_path
        metadata_path = self._get_metadata_path(file_path)

        try:
            if abs_path.exists():
                os.remove(abs_path)
            if metadata_path.exists():
                os.remove(metadata_path)
            return True
        except Exception:
            return False

    async def list_files(
        self, directory: Path, pattern: Optional[str] = None
    ) -> List[Path]:
        """ファイル一覧を取得する"""
        abs_path = self.base_path / directory
        if not abs_path.exists():
            return []

        files = []
        for root, _, filenames in os.walk(abs_path):
            root_path = Path(root)
            for filename in filenames:
                if pattern is None or Path(filename).match(pattern):
                    file_path = root_path / filename
                    files.append(file_path.relative_to(self.base_path))
        return files

    async def get_metadata(self, file_path: Path) -> Dict[str, Any]:
        """ファイルのメタデータを取得する"""
        metadata_path = self._get_metadata_path(file_path)
        if not metadata_path.exists():
            return {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

        with open(metadata_path, "r", encoding="utf-8") as f:
            return cast(Dict[str, Any], json.load(f))

    async def update_metadata(
        self, file_path: Path, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ファイルのメタデータを更新する"""
        current_metadata = await self.get_metadata(file_path)
        updated_metadata = {
            **current_metadata,
            **metadata,
            "updated_at": datetime.now().isoformat(),
        }

        metadata_path = self._get_metadata_path(file_path)
        self._ensure_metadata_directory(metadata_path)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(updated_metadata, f, ensure_ascii=False, indent=2)

        return updated_metadata
