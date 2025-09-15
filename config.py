import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL")

# Validate required environment variables
if not MONGODB_URL:
    raise ValueError("MONGODB_URL environment variable is required")

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