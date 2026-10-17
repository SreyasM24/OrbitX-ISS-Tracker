"""Canonical version constants for OrbitX.

This is a leaf module with zero dependencies to guarantee clean, circular-free imports.
"""

from __future__ import annotations

__version__ = "1.2.1"
APP_VERSION = f"v{__version__}"

__all__ = ["__version__", "APP_VERSION"]
