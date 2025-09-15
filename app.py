"""
Main entry point for Hugging Face Spaces deployment
This file redirects to the actual Streamlit app
"""

import subprocess
import sys
import os
from pathlib import Path

# Add the current directory to the path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Run the Streamlit app with the correct port for Hugging Face Spaces
subprocess.run([
    sys.executable, "-m", "streamlit", "run", "byte_extractor_app.py",
    "--server.port", "7860",  # Hugging Face Spaces default port
    "--server.address", "0.0.0.0"
])
