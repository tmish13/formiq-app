"""Performance tests for storage operations."""
import os
import time
import pytest
import asyncio
from pathlib import Path
from fastapi import UploadFile
from typing import List
from uuid import uuid4

from app.core.storage import LocalStorageProvider
from app.exceptions import VideoProcessingError

@pytest.fixture(scope="module")
def perf_storage_dir():
    """Create a test directory for performance testing."""
    test_dir = Path("/tmp/test_storage_perf")
    if test_dir.exists():
        for file in test_dir.glob("**/*"):
            if file.is_file():
                file.unlink()
    else:
        test_dir.mkdir(parents=True)
    yield test_dir
    # Clean up files but keep directory for reuse
    for file in test_dir.glob("**/*"):
        if file.is_file():
            file.unlink()

@pytest.fixture(scope="module")
def perf_storage_provider(perf_storage_dir):
    """Create a storage provider for performance testing."""
    return LocalStorageProvider(
        base_dir=str(perf_storage_dir),
        base_url="http://test.local/uploads"
    )

async def create_test_file(size_mb: int, path: Path) -> UploadFile:
    """Create a test file of specified size.
    
    Args:
        size_mb: Size in megabytes
        path: Path to create file at
        
    Returns:
        UploadFile: FastAPI UploadFile instance
    """
    size_bytes = size_mb * 1024 * 1024
    chunk_size = 1024 * 1024  # 1MB chunks
    
    with open(path, "wb") as f:
        remaining = size_bytes
        while remaining > 0:
            chunk = min(remaining, chunk_size)
            f.write(b"0" * chunk)
            remaining -= chunk
    
    return UploadFile(
        filename=path.name,
        file=path.open("rb"),
        content_type="video/mp4"
    )

class TestStoragePerformance:
    """Performance tests for storage operations."""

    @pytest.mark.benchmark
    async def test_upload_speed(self, perf_storage_provider, tmp_path):
        """Test upload speed for different file sizes."""
        sizes = [1, 10, 50, 100]  # File sizes in MB
        results = []
        
        for size in sizes:
            file_path = tmp_path / f"test_{size}mb.mp4"
            file = await create_test_file(size, file_path)
            
            try:
                start_time = time.time()
                object_name = f"videos/perf/test_{size}mb_{uuid4()}.mp4"
                
                await perf_storage_provider.upload_file(
                    file.file,
                    object_name,
                    content_type="video/mp4"
                )
                
                duration = time.time() - start_time
                speed_mbps = size / duration
                
                results.append({
                    "size_mb": size,
                    "duration_seconds": duration,
                    "speed_mbps": speed_mbps
                })
                
            finally:
                await file.close()
        
        # Log results
        for result in results:
            print(f"Upload {result['size_mb']}MB: "
                  f"{result['duration_seconds']:.2f}s "
                  f"({result['speed_mbps']:.2f} MB/s)")
        
        # Assert minimum upload speed (adjust based on system capabilities)
        assert all(r["speed_mbps"] > 1.0 for r in results), "Upload speed too slow"

    @pytest.mark.benchmark
    async def test_concurrent_upload_performance(
        self,
        perf_storage_provider,
        tmp_path
    ):
        """Test performance of concurrent uploads."""
        concurrent_uploads = 10
        file_size_mb = 5
        
        async def upload_file(index: int) -> float:
            file_path = tmp_path / f"concurrent_{index}.mp4"
            file = await create_test_file(file_size_mb, file_path)
            
            try:
                start_time = time.time()
                object_name = f"videos/perf/concurrent_{index}_{uuid4()}.mp4"
                
                await perf_storage_provider.upload_file(
                    file.file,
                    object_name,
                    content_type="video/mp4"
                )
                
                return time.time() - start_time
            finally:
                await file.close()
        
        # Run concurrent uploads
        start_time = time.time()
        durations = await asyncio.gather(
            *[upload_file(i) for i in range(concurrent_uploads)]
        )
        total_duration = time.time() - start_time
        
        # Calculate statistics
        avg_duration = sum(durations) / len(durations)
        total_size_mb = file_size_mb * concurrent_uploads
        throughput = total_size_mb / total_duration
        
        print(f"Concurrent Upload Stats:")
        print(f"Total files: {concurrent_uploads}")
        print(f"Total size: {total_size_mb}MB")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Average per file: {avg_duration:.2f}s")
        print(f"Throughput: {throughput:.2f} MB/s")
        
        # Assert reasonable performance
        assert throughput > 5.0, "Concurrent upload throughput too low"
        assert max(durations) < 30.0, "Individual upload took too long"

    @pytest.mark.benchmark
    async def test_delete_performance(self, perf_storage_provider, tmp_path):
        """Test performance of file deletion operations."""
        # Create test files
        file_count = 100
        files_to_delete: List[str] = []
        
        # Upload files first
        for i in range(file_count):
            file_path = tmp_path / f"to_delete_{i}.mp4"
            file = await create_test_file(1, file_path)  # 1MB files
            
            try:
                object_name = f"videos/perf/to_delete_{i}_{uuid4()}.mp4"
                await perf_storage_provider.upload_file(
                    file.file,
                    object_name,
                    content_type="video/mp4"
                )
                files_to_delete.append(object_name)
            finally:
                await file.close()
        
        # Measure deletion performance
        start_time = time.time()
        delete_tasks = [
            perf_storage_provider.delete_file(file)
            for file in files_to_delete
        ]
        await asyncio.gather(*delete_tasks)
        duration = time.time() - start_time
        
        deletions_per_second = file_count / duration
        print(f"Deletion performance:")
        print(f"Files deleted: {file_count}")
        print(f"Total duration: {duration:.2f}s")
        print(f"Deletions per second: {deletions_per_second:.2f}")
        
        # Assert reasonable deletion speed
        assert deletions_per_second > 10.0, "Deletion speed too slow"

    @pytest.mark.benchmark
    async def test_storage_operation_under_load(
        self,
        perf_storage_provider,
        tmp_path
    ):
        """Test storage operations under simulated load."""
        async def mixed_operations(index: int):
            # Upload
            file_path = tmp_path / f"load_test_{index}.mp4"
            file = await create_test_file(1, file_path)  # 1MB file
            
            try:
                object_name = f"videos/load/file_{index}_{uuid4()}.mp4"
                await perf_storage_provider.upload_file(
                    file.file,
                    object_name,
                    content_type="video/mp4"
                )
                
                # List files
                await perf_storage_provider.list_files()
                
                # Delete
                await perf_storage_provider.delete_file(object_name)
                
            finally:
                await file.close()
        
        # Run 50 concurrent mixed operations
        start_time = time.time()
        await asyncio.gather(*[mixed_operations(i) for i in range(50)])
        duration = time.time() - start_time
        
        operations_per_second = 150 / duration  # 3 operations per task
        print(f"Mixed operations under load:")
        print(f"Total operations: 150")
        print(f"Duration: {duration:.2f}s")
        print(f"Operations per second: {operations_per_second:.2f}")
        
        # Assert reasonable performance under load
        assert operations_per_second > 5.0, "Performance under load too low" 