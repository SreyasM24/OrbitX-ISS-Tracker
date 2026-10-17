"""OrbitX backend: orbital elements, orbital maths, validation and pass prediction.

Nothing in this package imports Streamlit, so it can be tested and reused on its own.
"""

from backend.config import APP_VERSION

__version__ = APP_VERSION.lstrip("v")

__all__ = ["__version__", "APP_VERSION"]
