import streamlit as st
import sys
import os
from pathlib import Path

# Add current directory to Python path to find modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the modules directly
import byte_extractor_service
import logger_config

# Get the required functions and variables
collection = byte_extractor_service.collection
get_paginated_bytes_with_query = byte_extractor_service.get_paginated_bytes_with_query
update_summary_review_status = byte_extractor_service.update_summary_review_status
update_original_article_review_status = byte_extractor_service.update_original_article_review_status
logger = logger_config.logger

# -------------------------
# Streamlit Page Config
# -------------------------
logger.info("Initializing Heartfulness Article Viewer application")
st.set_page_config(
    page_title="Heartfulness Article Viewer",
    page_icon="📖",
    layout="wide"
)
logger.info("Streamlit page configuration set successfully")

# -------------------------
# Sidebar
# -------------------------
logger.info("Setting up sidebar navigation")
st.sidebar.title("📚 Heartfulness Extractor")
page = st.sidebar.radio("Navigation", [
    "📂 View Extracted Articles",
    "📊 Article Comparison Viewer"
])
logger.info(f"Selected page: {page}")



# -------------------------
# View Extracted Articles
# -------------------------
if page == "📂 View Extracted Articles":
    logger.info("Rendering View Extracted Articles page - Maintenance Mode")
    st.title("📂 View Extracted Articles from MongoDB")
    
    # Maintenance message
    st.warning("""
    **This is a message from old article view app:**
    
    We are down today. Please come back tomorrow.
    
    **To read and compare articles:**
    
    Go to the page '📊 Article Comparison Viewer' in the sidebar, upload the original articles markdown file in one place, and upload summary markdown file in the second place and you can start reading the articles.
    """)
    
    logger.info("Maintenance mode message displayed")

# -------------------------
# Article Comparison Viewer
# -------------------------
elif page == "📊 Article Comparison Viewer":
    logger.info("Rendering Article Comparison Viewer page")
    st.title("📊 Article Comparison Viewer")
    st.markdown("Compare original articles with their summaries side by side.")
    
    # Read and embed the HTML file
    html_file_path = Path(__file__).parent / "article_comparison_viewer.html"
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Embed the HTML component with full height
    st.components.v1.html(html_content, height=800, scrolling=True)

