# tests/conftest.py
import os
import sys

# Add the project root directory to sys.path so that "import app" works
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
