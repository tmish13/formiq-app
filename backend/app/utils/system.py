"""System utilities for monitoring and metrics."""
import os
import time
import psutil
from typing import Dict, Any, Optional


def get_memory_usage(process: Optional[psutil.Process] = None) -> Dict[str, Any]:
    """
    Get memory usage metrics for the system and optionally a specific process.
    
    Args:
        process: Optional process to get memory info for
        
    Returns:
        Dictionary with memory usage metrics
    """
    # System memory
    memory = psutil.virtual_memory()
    result = {
        "system": {
            "total_mb": round(memory.total / (1024 * 1024), 2),
            "available_mb": round(memory.available / (1024 * 1024), 2),
            "used_mb": round(memory.used / (1024 * 1024), 2),
            "percent": memory.percent
        }
    }
    
    # Process memory if provided
    if process:
        try:
            mem_info = process.memory_info()
            result["process"] = {
                "rss_mb": round(mem_info.rss / (1024 * 1024), 2),  # Resident Set Size
                "vms_mb": round(mem_info.vms / (1024 * 1024), 2),  # Virtual Memory Size
                "percent": round(process.memory_percent(), 2),
                "page_faults": mem_info.pfaults if hasattr(mem_info, 'pfaults') else None,
                "page_faults_per_second": None  # Set in the memory growth function
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            result["process"] = {"error": "Could not access process memory info"}
    
    return result


def get_cpu_usage(process: Optional[psutil.Process] = None) -> float:
    """
    Get CPU usage percent for the system or a specific process.
    
    Args:
        process: Optional process to get CPU usage for
        
    Returns:
        CPU usage percentage
    """
    if process:
        try:
            # Non-blocking CPU measurement with interval=None returns
            # value since last call or process start
            return process.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0
    else:
        # System-wide CPU usage
        return psutil.cpu_percent(interval=0.1)


def get_disk_usage(path: str = None) -> Dict[str, Any]:
    """
    Get disk usage metrics for a specific path.
    
    Args:
        path: Path to check disk usage for, defaults to current directory
        
    Returns:
        Dictionary with disk usage metrics
    """
    if not path:
        path = os.getcwd()
        
    try:
        disk = psutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
            "used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
            "free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
            "percent": disk.percent
        }
    except (OSError, FileNotFoundError):
        return {
            "path": path,
            "error": f"Path not found or not accessible: {path}"
        }


def monitor_memory_growth(process: psutil.Process, interval: int = 60, samples: int = 5) -> Dict[str, Any]:
    """
    Monitor memory growth over time to detect potential memory leaks.
    
    Args:
        process: Process to monitor
        interval: Interval between measurements in seconds
        samples: Number of samples to take
        
    Returns:
        Dictionary with memory growth metrics
    """
    try:
        measurements = []
        
        for _ in range(samples):
            mem_percent = process.memory_percent()
            mem_info = process.memory_info()
            measurements.append({
                "timestamp": time.time(),
                "rss_mb": mem_info.rss / (1024 * 1024),
                "percent": mem_percent
            })
            
            if _ < samples - 1:  # Don't sleep after the last sample
                time.sleep(interval)
        
        # Calculate growth rate
        if len(measurements) > 1:
            first = measurements[0]
            last = measurements[-1]
            time_diff = last["timestamp"] - first["timestamp"]
            percent_diff = last["percent"] - first["percent"]
            mb_diff = last["rss_mb"] - first["rss_mb"]
            
            growth_per_hour = 0
            if time_diff > 0:
                growth_per_hour = (mb_diff / time_diff) * 3600  # MB per hour
            
            return {
                "measurements": measurements,
                "growth_mb_per_hour": round(growth_per_hour, 2),
                "growth_percent": round(percent_diff, 2),
                "duration_seconds": round(time_diff, 2)
            }
        
        return {
            "measurements": measurements,
            "error": "Not enough samples to calculate growth"
        }
        
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {"error": "Process not accessible"}


def get_network_stats() -> Dict[str, Any]:
    """
    Get network interface statistics.
    
    Returns:
        Dictionary with network stats by interface
    """
    try:
        net_io = psutil.net_io_counters(pernic=True)
        result = {}
        
        for interface, stats in net_io.items():
            result[interface] = {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv,
                "errin": stats.errin if hasattr(stats, 'errin') else None,
                "errout": stats.errout if hasattr(stats, 'errout') else None,
                "dropin": stats.dropin if hasattr(stats, 'dropin') else None,
                "dropout": stats.dropout if hasattr(stats, 'dropout') else None
            }
            
        return result
    except Exception:
        return {"error": "Could not retrieve network statistics"} 