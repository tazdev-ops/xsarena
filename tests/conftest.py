"""Pytest configuration for XSArena tests."""
import sys
import os

# Add src to path so we can import xsarena modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))