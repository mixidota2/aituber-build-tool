"""ストレージサービスの基本定義"""

from typing import BinaryIO, Optional, List, Dict, Any
from abc import ABC, abstractmethod
from pathlib import Path


class StorageService(ABC):
    """ストレージサービスの基底クラス"""

    @abstractmethod
    async def save_file(self, file: BinaryIO, path: str) -> str:
        """ファイルを保存

        Args:
            file: 保存するファイルオブジェクト
            path: 保存先のパス

        Returns:
            str: 保存されたファイルの完全なパス
        """
        pass

    @abstractmethod
    async def get_file(self, path: str) -> Optional[Path]:
        """ファイルを取得

        Args:
            path: ファイルのパス

        Returns:
            Optional[Path]: ファイルのパス。存在しない場合はNone
        """
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """ファイルを削除

        Args:
            path: 削除するファイルのパス

        Returns:
            bool: 削除に成功した場合はTrue
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """ファイルの存在確認

        Args:
            path: 確認するファイルのパス

        Returns:
            bool: ファイルが存在する場合はTrue
        """
        pass


class BaseStorageService(ABC):
    """ストレージサービスの基底クラス"""

    @abstractmethod
    async def save_file(
        self,
        file_path: Path,
        content: bytes | str | BinaryIO,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """ファイルを保存する"""
        pass

    @abstractmethod
    async def get_file(self, file_path: Path) -> bytes:
        """ファイルを取得する"""
        pass

    @abstractmethod
    async def delete_file(self, file_path: Path) -> bool:
        """ファイルを削除する"""
        pass

    @abstractmethod
    async def list_files(
        self,
        directory: Path,
        pattern: Optional[str] = None
    ) -> List[Path]:
        """ファイル一覧を取得する"""
        pass

    @abstractmethod
    async def get_metadata(self, file_path: Path) -> Dict[str, Any]:
        """ファイルのメタデータを取得する"""
        pass

    @abstractmethod
    async def update_metadata(
        self,
        file_path: Path,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ファイルのメタデータを更新する"""
        pass 