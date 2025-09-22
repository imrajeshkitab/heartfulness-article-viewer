#!/usr/bin/env python3
"""
Script to query MongoDB collection for documents with specific criteria:
- Best_byte: false
- Summary_review_status: accepted

This script will list UUIDs and provide a count of matching documents.
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
from logger_config import logger

# Load environment variables
load_dotenv()

def get_mongodb_connection():
    """Get MongoDB connection using environment variables."""
    mongodb_url = os.getenv("MONGODB_URL")
    
    if not mongodb_url:
        logger.error("MONGODB_URL not found in environment variables")
        raise ValueError(
            "MONGODB_URL environment variable is required. "
            "Please set it in your environment or create a .env file."
        )
    
    try:
        client = MongoClient(mongodb_url)
        # Test the connection
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

def query_documents():
    """Query documents with specified criteria and return UUIDs and count."""
    try:
        # Get MongoDB connection
        client = get_mongodb_connection()
        db = client["kitab_prod"]
        collection = db["HFN_raw_articles"]
        
        # Define the query criteria
        query = {
            "Best_byte": False,
            "Summary_review_status": "accepted"
        }
        
        logger.info(f"Querying collection with criteria: {query}")
        
        # Get total count
        total_count = collection.count_documents(query)
        logger.info(f"Total documents matching criteria: {total_count}")
        
        # Get all matching documents (only _id field for efficiency)
        documents = list(collection.find(query, {"_id": 1}))
        
        # Extract UUIDs (MongoDB _id field)
        uuids = [str(doc["_id"]) for doc in documents]
        
        return uuids, total_count
        
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        raise
    finally:
        if 'client' in locals():
            client.close()

def main():
    """Main function to execute the query and display results."""
    try:
        logger.info("Starting document query...")
        
        # Query documents
        uuids, total_count = query_documents()
        
        # Display results
        print("\n" + "="*80)
        print("QUERY RESULTS")
        print("="*80)
        print(f"Criteria: Best_byte = false AND Summary_review_status = 'accepted'")
        print(f"Total number of documents: {total_count}")
        print("="*80)
        
        if uuids:
            print("\nDocument UUIDs:")
            print("-" * 40)
            for i, uuid in enumerate(uuids, 1):
                print(f"{i:3d}. {uuid}")
        else:
            print("\nNo documents found matching the criteria.")
        
        print("\n" + "="*80)
        print(f"SUMMARY: Found {total_count} documents with Best_byte=false and Summary_review_status='accepted'")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
