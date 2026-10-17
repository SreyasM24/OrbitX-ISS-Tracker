"""OrbitX backend: orbital elements, orbital maths, validation and pass prediction.

Nothing in this package imports Streamlit, so it can be tested and reused on its own.
"""

from __future__ import annotations

from backend.version import APP_VERSION, __version__

__all__ = ["__version__", "APP_VERSION"]
