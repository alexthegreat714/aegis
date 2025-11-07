"""
System health monitoring utilities.

Collects CPU, memory, and active window information.
"""

import psutil
from typing import Optional, Dict, Any


class HealthMonitor:
    """Monitor system health metrics."""

    @staticmethod
    def get_cpu_percent() -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0

    @staticmethod
    def get_memory_percent() -> float:
        """Get current memory usage percentage."""
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0

    @staticmethod
    def get_active_window() -> Optional[str]:
        """
        Get active window title (Windows only).

        Returns:
            Window title or None if unavailable
        """
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            return title if title else None
        except Exception:
            # pywin32 not available or not on Windows
            return None

    @classmethod
    def get_health_snapshot(
        self,
        include_cpu: bool = True,
        include_memory: bool = True,
        include_window: bool = True
    ) -> Dict[str, Any]:
        """
        Get complete health snapshot.

        Args:
            include_cpu: Include CPU metrics
            include_memory: Include memory metrics
            include_window: Include active window

        Returns:
            Dictionary with health metrics
        """
        snapshot = {}

        if include_cpu:
            snapshot['cpu_percent'] = self.get_cpu_percent()

        if include_memory:
            snapshot['memory_percent'] = self.get_memory_percent()

        if include_window:
            window = self.get_active_window()
            if window:
                snapshot['active_window'] = window

        return snapshot
