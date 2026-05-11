"""
Shared pytest fixtures and configuration.
Path manipulation ensures backend imports resolve correctly
when running pytest from the project root.
"""
import sys
import os

# Add project root to PYTHONPATH so `backend.*` imports work
sys.path.insert(0, os.path.dirname(__file__))
