"""
Main entry point for Hugging Face Spaces deployment
This file redirects to the actual Streamlit app
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add the pages directory to the path
pages_dir = Path(__file__).parent / "pages"
sys.path.insert(0, str(pages_dir))

# Import and run the main app
from byte_extractor_app import *
