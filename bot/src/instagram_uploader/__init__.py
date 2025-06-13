"""
Instagram Uploader module - Playwright implementation

Provides tools for automating Instagram account interactions.
"""

__version__ = "1.0.0"

# This file makes the directory a Python package
# Import config from config.toml
import tomli
import os

# Load config from TOML file
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")
with open(config_path, "rb") as f:
    config = tomli.load(f)

# Export variables referenced in other modules
__all__ = ['config'] 