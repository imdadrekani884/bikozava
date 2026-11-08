"""
Bikozava — Routes Package (`app/routes/__init__.py`)
"""
from .admin import admin_bp
from .public import public_bp

__all__ = ["admin_bp", "public_bp"]
