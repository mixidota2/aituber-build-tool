"""ストレージサービスパッケージ"""

from .base import StorageService
from .local import LocalStorageService

__all__ = ['StorageService', 'LocalStorageService'] 