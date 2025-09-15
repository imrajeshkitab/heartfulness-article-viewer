import os
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
# This is for local development only
load_dotenv()

# MongoDB Configuration
# Priority: 1. Environment variable, 2. .env file, 3. Error
MONGODB_URL = os.getenv("MONGODB_URL")

# Validate required environment variables
if not MONGODB_URL:
    raise ValueError(
        "MONGODB_URL environment variable is required. "
        "Please set it in Hugging Face Spaces secrets or create a .env file for local development."
    )

# Database Configuration
DB_NAME = "kitab_prod"
COLLECTION_NAME = "extracted_wisdom_byte"

# App Configuration
APP_TITLE = "Heartfulness Article Viewer"
APP_ICON = "📖"
LAYOUT = "wide"

# Pagination Configuration
DEFAULT_PAGE_SIZE = 10

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = "logs"