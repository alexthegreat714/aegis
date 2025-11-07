"""
System observation module for Aegis agent.

Day 4: Collects system context for autonomous operation.
"""

from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
import platform
import time

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    PYGETWINDOW_AVAILABLE = False


class SystemObservation(TypedDict, total=False):
    """
    Typed dictionary for system observations.

    Day 4: Structured observation data passed to LLM.
    """
    timestamp: str
    active_window: Optional[str]
    processes: List[Dict[str, Any]]
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    platform: str
    python_version: str
    uptime_seconds: float
    process_count: int
    top_cpu_processes: List[Dict[str, Any]]


class SystemObserver:
    """
    Collects system observations for autonomous agent operation.

    Day 4: Provides enhanced context for multi-cycle runs.
    """

    def __init__(self):
        """Initialize system observer."""
        self.start_time = time.time()
        self.last_observation_time = None

    def observe(self) -> SystemObservation:
        """
        Collect current system state.

        Returns:
            SystemObservation dict with current context
        """
        observation: SystemObservation = {
            "timestamp": datetime.now().isoformat(),
            "active_window": self._get_active_window(),
            "processes": self._get_process_list(),
            "cpu_percent": self._get_cpu_percent(),
            "memory_percent": self._get_memory_percent(),
            "disk_percent": self._get_disk_percent(),
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "uptime_seconds": time.time() - self.start_time,
            "process_count": self._get_process_count(),
            "top_cpu_processes": self._get_top_cpu_processes(limit=5)
        }

        self.last_observation_time = time.time()
        return observation

    def _get_active_window(self) -> Optional[str]:
        """
        Get active window title.

        Returns:
            Window title or None if unavailable
        """
        if not PYGETWINDOW_AVAILABLE:
            return None

        try:
            active = gw.getActiveWindow()
            if active:
                return active.title
        except Exception:
            pass

        return None

    def _get_process_list(self) -> List[Dict[str, Any]]:
        """
        Get list of running processes.

        Returns:
            List of process dictionaries
        """
        if not PSUTIL_AVAILABLE:
            return []

        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "status": proc.info['status']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        return processes

    def _get_cpu_percent(self) -> float:
        """
        Get current CPU usage percentage.

        Returns:
            CPU percentage (0-100)
        """
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0

    def _get_memory_percent(self) -> float:
        """
        Get current memory usage percentage.

        Returns:
            Memory percentage (0-100)
        """
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0

    def _get_disk_percent(self) -> float:
        """
        Get current disk usage percentage.

        Returns:
            Disk percentage (0-100)
        """
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            return psutil.disk_usage('/').percent
        except Exception:
            return 0.0

    def _get_process_count(self) -> int:
        """
        Get total number of running processes.

        Returns:
            Process count
        """
        if not PSUTIL_AVAILABLE:
            return 0

        try:
            return len(psutil.pids())
        except Exception:
            return 0

    def _get_top_cpu_processes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top CPU-consuming processes.

        Args:
            limit: Number of top processes to return

        Returns:
            List of process dictionaries sorted by CPU usage
        """
        if not PSUTIL_AVAILABLE:
            return []

        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    cpu = proc.info['cpu_percent']
                    if cpu is not None:
                        processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cpu_percent": cpu
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage and take top N
            processes.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
            return processes[:limit]
        except Exception:
            return []

    def get_idle_time(self) -> float:
        """
        Get time since last observation.

        Returns:
            Seconds since last observation, or 0 if first observation
        """
        if self.last_observation_time is None:
            return 0.0

        return time.time() - self.last_observation_time

    def to_summary_dict(self, observation: SystemObservation) -> Dict[str, Any]:
        """
        Convert observation to compact summary for logging.

        Args:
            observation: Full system observation

        Returns:
            Compact summary dictionary
        """
        return {
            "timestamp": observation.get("timestamp"),
            "active_window": observation.get("active_window"),
            "cpu_percent": observation.get("cpu_percent"),
            "memory_percent": observation.get("memory_percent"),
            "process_count": observation.get("process_count"),
            "uptime_seconds": observation.get("uptime_seconds")
        }
