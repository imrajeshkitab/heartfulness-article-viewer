import os
import sys
from typing import List, Dict
from pymongo import MongoClient
from .logger_config import logger

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import MONGODB_URL, DB_NAME, COLLECTION_NAME
    logger.info("Configuration loaded successfully from config.py")
except ImportError:
    # Fallback for when config.py is not available
    logger.info("config.py not found, using direct environment variable access")
    from dotenv import load_dotenv
    load_dotenv()  # This will silently fail if .env doesn't exist, which is fine
    
    MONGODB_URL = os.getenv("MONGODB_URL")
    DB_NAME = "kitab_prod"
    COLLECTION_NAME = "extracted_wisdom_byte"
    
    if not MONGODB_URL:
        logger.error("MONGODB_URL not found in environment variables")
        raise ValueError(
            "MONGODB_URL environment variable is required. "
            "Please set it in Hugging Face Spaces secrets or create a .env file for local development."
        )
    
    logger.info("Using fallback configuration from environment variables")

logger.info(f"MongoDB URL loaded: {MONGODB_URL[:20]}...")

# -------------------------
# MongoDB Setup
# -------------------------
logger.info("Initializing MongoDB connection")
try:
    client_mongo = MongoClient(MONGODB_URL)
    db = client_mongo[DB_NAME]
    collection = db[COLLECTION_NAME]
    logger.info("MongoDB connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise


def get_paginated_bytes_with_query(query: dict, page_number: int, page_size: int = 10):
    """
    Fetch paginated articles from MongoDB using a custom query.
    
    Args:
        query (dict): MongoDB query dictionary
        page_number (int): Page number to fetch
        page_size (int): Number of documents per page
        
    Returns:
        dict: Pagination result with page_number, total_pages, and docs
    """
    logger.info(f"Fetching paginated articles - Page: {page_number}, Size: {page_size}")
    logger.debug(f"Query: {query}")
    
    try:
        # Calculate skip value
        skip = (page_number - 1) * page_size
        logger.debug(f"Calculated skip value: {skip}")
        
        # Get total count for pagination
        logger.info("Counting total documents matching query")
        total_docs = collection.count_documents(query)
        total_pages = (total_docs + page_size - 1) // page_size  # Ceiling division
        logger.info(f"Total documents: {total_docs}, Total pages: {total_pages}")
        
        # Fetch documents with pagination
        logger.info(f"Fetching documents with skip={skip}, limit={page_size}")
        docs = list(collection.find(query).skip(skip).limit(page_size))
        logger.info(f"Retrieved {len(docs)} documents")
        
        result = {
            "page_number": page_number,
            "total_pages": total_pages,
            "docs": docs
        }
        
        logger.info(f"Successfully returned pagination result: {len(docs)} docs on page {page_number} of {total_pages}")
        return result
        
    except Exception as e:
        logger.error(f"Error in get_paginated_bytes_with_query: {e}", exc_info=True)
        return {
            "page_number": 1,
            "total_pages": 0,
            "docs": []
        }


def update_summary_review_status(article_id: str, status: str) -> bool:
    """
    Update article's summary review status.
    
    Args:
        article_id (str): MongoDB document _id
        status (str): "accepted" or "rejected"
        
    Returns:
        bool: True if update successful, False otherwise
    """
    logger.info(f"Updating summary review status for article {article_id} to '{status}'")
    
    try:
        from bson import ObjectId
        
        # Convert string ID to ObjectId
        logger.debug(f"Converting article_id '{article_id}' to ObjectId")
        object_id = ObjectId(article_id)
        
        # Update the document
        logger.info(f"Executing MongoDB update operation")
        result = collection.update_one(
            {"_id": object_id},
            {"$set": {"summary_review_status": status}}
        )
        
        success = result.modified_count > 0
        logger.info(f"Update result - Modified count: {result.modified_count}, Success: {success}")
        
        if success:
            logger.info(f"Successfully updated article {article_id} status to '{status}'")
        else:
            logger.warning(f"No documents were modified for article {article_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error updating summary review status for article {article_id}: {e}", exc_info=True)
        return False