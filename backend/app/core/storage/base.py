"""Base storage provider interface."""
from typing import Optional, Dict, Any, BinaryIO, Tuple, List

class StorageProvider:
    """Base storage provider interface."""
    
    async def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public: bool = False,
    ) -> str:
        """Upload a file to storage."""
        raise NotImplementedError()
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete a file from storage."""
        raise NotImplementedError()
    
    async def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List files in storage."""
        raise NotImplementedError()
    
    async def get_file(self, object_name: str) -> Tuple[bytes, Dict[str, Any]]:
        """Get a file from storage."""
        raise NotImplementedError()
    
    @staticmethod
    def get_key_from_url(url: str) -> str:
        """Extract the key from a URL."""
        raise NotImplementedError() 