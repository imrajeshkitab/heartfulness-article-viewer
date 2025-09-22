#!/usr/bin/env python3
"""
Byte Categorization Script
Categorizes MongoDB documents using OpenAI API with parallel processing
"""

import os
import sys
import csv
import asyncio
import aiohttp
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('categorization.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ByteCategorizer:
    def __init__(self):
        self.mongodb_url = os.getenv('MONGODB_URL')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.mongodb_url:
            raise ValueError("MONGODB_URL not found in environment variables")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = MongoClient(self.mongodb_url)
        self.db = None
        self.collection = None
        self.categories = []
        self.uuid_data = []
        
    def get_available_databases(self) -> List[str]:
        """Get list of available databases"""
        try:
            return self.client.list_database_names()
        except Exception as e:
            logger.error(f"Error fetching databases: {e}")
            return []
    
    def get_available_collections(self, db_name: str) -> List[str]:
        """Get list of available collections in a database"""
        try:
            db = self.client[db_name]
            return db.list_collection_names()
        except Exception as e:
            logger.error(f"Error fetching collections for {db_name}: {e}")
            return []
    
    def load_csv_data(self, csv_path: str, uuid_column: str) -> List[Dict]:
        """Load CSV data with UUIDs"""
        try:
            df = pd.read_csv(csv_path)
            if uuid_column not in df.columns:
                raise ValueError(f"Column '{uuid_column}' not found in CSV")
            
            return df[uuid_column].dropna().tolist()
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return []
    
    def load_categories(self, csv_path: str, categories_column: str) -> List[str]:
        """Load categories from CSV"""
        try:
            df = pd.read_csv(csv_path)
            if categories_column not in df.columns:
                raise ValueError(f"Column '{categories_column}' not found in CSV")
            
            return df[categories_column].dropna().unique().tolist()
        except Exception as e:
            logger.error(f"Error loading categories: {e}")
            return []
    
    def check_field_existence(self, uuids: List[str], field_name: str) -> Dict[str, Any]:
        """Check which documents have the field to categorize"""
        try:
            pipeline = [
                {"$match": {"uuid": {"$in": uuids}}},
                {"$project": {
                    "uuid": 1,
                    "has_field": {"$cond": [{"$ne": [f"${field_name}", None]}, True, False]},
                    "field_value": f"${field_name}"
                }}
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            found_uuids = [doc["uuid"] for doc in results]
            missing_uuids = [uuid for uuid in uuids if uuid not in found_uuids]
            
            has_field_count = sum(1 for doc in results if doc["has_field"])
            no_field_count = len(results) - has_field_count
            
            return {
                "total_uuids": len(uuids),
                "found_in_db": len(results),
                "missing_from_db": len(missing_uuids),
                "has_field": has_field_count,
                "no_field": no_field_count,
                "missing_uuids": missing_uuids,
                "documents": results
            }
        except Exception as e:
            logger.error(f"Error checking field existence: {e}")
            return {}
    
    async def categorize_with_openai(self, content: str, categories: List[str]) -> Optional[str]:
        """Categorize content using OpenAI API"""
        try:
            prompt = f"""
            Categorize the following content into one of these categories: {', '.join(categories)}
            
            Content: {content}...
            
            Return only the category name that best fits the content.
            """
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "You are a content categorization expert. Return only the category name."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()
                    else:
                        logger.error(f"OpenAI API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error categorizing content: {e}")
            return None
    
    async def process_document(self, doc: Dict, field_name: str, output_field: str, categories: List[str]) -> Dict[str, Any]:
        """Process a single document for categorization"""
        try:
            uuid = doc["uuid"]
            
            if not doc["has_field"]:
                return {
                    "uuid": uuid,
                    "status": "skipped",
                    "reason": f"Field '{field_name}' not found",
                    "category": None
                }
            
            content = doc["field_value"]
            if not content or not content.strip():
                return {
                    "uuid": uuid,
                    "status": "skipped",
                    "reason": f"Field '{field_name}' is empty",
                    "category": None
                }
            
            category = await self.categorize_with_openai(content, categories)
            
            if category and category in categories:
                return {
                    "uuid": uuid,
                    "status": "categorized",
                    "category": category,
                    "content_preview": content[:100] + "..." if len(content) > 100 else content
                }
            else:
                return {
                    "uuid": uuid,
                    "status": "failed",
                    "reason": f"Invalid category returned: {category}",
                    "category": None
                }
                
        except Exception as e:
            logger.error(f"Error processing document {doc.get('uuid', 'unknown')}: {e}")
            return {
                "uuid": doc.get("uuid", "unknown"),
                "status": "error",
                "reason": str(e),
                "category": None
            }
    
    async def process_documents_parallel(self, documents: List[Dict], field_name: str, output_field: str, categories: List[str], max_workers: int = 10) -> List[Dict]:
        """Process documents in parallel"""
        semaphore = asyncio.Semaphore(max_workers)
        
        async def process_with_semaphore(doc):
            async with semaphore:
                return await self.process_document(doc, field_name, output_field, categories)
        
        tasks = [process_with_semaphore(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "uuid": documents[i].get("uuid", "unknown"),
                    "status": "error",
                    "reason": str(result),
                    "category": None
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def update_documents(self, results: List[Dict], output_field: str) -> Dict[str, int]:
        """Update documents with categorized results"""
        update_stats = {"success": 0, "failed": 0, "skipped": 0}
        
        for result in results:
            if result["status"] == "categorized":
                try:
                    self.collection.update_one(
                        {"uuid": result["uuid"]},
                        {"$set": {output_field: result["category"]}}
                    )
                    update_stats["success"] += 1
                    logger.info(f"Updated {result['uuid']} with category: {result['category']}")
                except Exception as e:
                    logger.error(f"Failed to update {result['uuid']}: {e}")
                    update_stats["failed"] += 1
            else:
                update_stats["skipped"] += 1
        
        return update_stats
    
    def print_summary(self, field_check: Dict, results: List[Dict], update_stats: Dict):
        """Print summary of the categorization process"""
        print("\n" + "="*60)
        print("CATEGORIZATION SUMMARY")
        print("="*60)
        
        print(f"\n📊 FIELD EXISTENCE CHECK:")
        print(f"   Total UUIDs in CSV: {field_check['total_uuids']}")
        print(f"   Found in MongoDB: {field_check['found_in_db']}")
        print(f"   Missing from MongoDB: {field_check['missing_from_db']}")
        print(f"   Have field to categorize: {field_check['has_field']}")
        print(f"   Missing field: {field_check['no_field']}")
        
        if field_check['missing_uuids']:
            print(f"\n⚠️  MISSING UUIDs from MongoDB:")
            for uuid in field_check['missing_uuids'][:10]:  # Show first 10
                print(f"   - {uuid}")
            if len(field_check['missing_uuids']) > 10:
                print(f"   ... and {len(field_check['missing_uuids']) - 10} more")
        
        print(f"\n🤖 CATEGORIZATION RESULTS:")
        categorized = [r for r in results if r["status"] == "categorized"]
        skipped = [r for r in results if r["status"] == "skipped"]
        failed = [r for r in results if r["status"] == "failed"]
        
        print(f"   Successfully categorized: {len(categorized)}")
        print(f"   Skipped: {len(skipped)}")
        print(f"   Failed: {len(failed)}")
        
        if categorized:
            print(f"\n📋 CATEGORIZATION PREVIEW:")
            for result in categorized[:5]:  # Show first 5
                print(f"   UUID: {result['uuid']}")
                print(f"   Category: {result['category']}")
                print(f"   Content: {result['content_preview']}")
                print()
        
        print(f"\n💾 UPDATE STATISTICS:")
        print(f"   Successfully updated: {update_stats['success']}")
        print(f"   Failed to update: {update_stats['failed']}")
        print(f"   Skipped: {update_stats['skipped']}")
        
        print("\n" + "="*60)

async def main():
    """Main function to run the categorization process"""
    categorizer = ByteCategorizer()
    
    try:
        # Get database selection
        print("Available databases:")
        databases = categorizer.get_available_databases()
        for i, db in enumerate(databases, 1):
            print(f"{i}. {db}")
        
        db_choice = int(input("\nSelect database (number): ")) - 1
        db_name = databases[db_choice]
        categorizer.db = categorizer.client[db_name]
        
        # Get collection selection
        print(f"\nAvailable collections in {db_name}:")
        collections = categorizer.get_available_collections(db_name)
        for i, coll in enumerate(collections, 1):
            print(f"{i}. {coll}")
        
        coll_choice = int(input("\nSelect collection (number): ")) - 1
        collection_name = collections[coll_choice]
        categorizer.collection = categorizer.db[collection_name]
        
        # Get CSV file paths and column names
        uuid_csv = input("\nEnter path to CSV with UUIDs: ").strip()
        uuid_column = input("Enter UUID column name: ").strip()
        
        categories_csv = input("\nEnter path to CSV with Categories: ").strip()
        categories_column = input("Enter Categories column name: ").strip()
        
        # Get field names
        field_to_categorize = input("\nEnter field name to categorize: ").strip()
        output_field = input("Enter output field name: ").strip()
        
        # Get max workers
        max_workers = int(input("\nEnter number of parallel workers (default 10): ") or "10")
        
        # Load data
        print("\nLoading data...")
        uuids = categorizer.load_csv_data(uuid_csv, uuid_column)
        categories = categorizer.load_categories(categories_csv, categories_column)
        
        if not uuids:
            print("No UUIDs found in CSV")
            return
        
        if not categories:
            print("No categories found in CSV")
            return
        
        print(f"Loaded {len(uuids)} UUIDs and {len(categories)} categories")
        
        # Check field existence
        print("\nChecking field existence...")
        field_check = categorizer.check_field_existence(uuids, field_to_categorize)
        
        # Check if output field exists
        sample_doc = categorizer.collection.find_one({"uuid": {"$in": uuids}})
        if sample_doc and output_field not in sample_doc:
            print(f"\n⚠️  WARNING: Output field '{output_field}' does not exist in the collection!")
            proceed = input("Do you want to continue? (y/N): ").strip().lower()
            if proceed != 'y':
                print("Operation cancelled.")
                return
        
        # Process documents
        print(f"\nProcessing {field_check['has_field']} documents with {max_workers} parallel workers...")
        documents_to_process = [doc for doc in field_check['documents'] if doc['has_field']]
        
        results = await categorizer.process_documents_parallel(
            documents_to_process, field_to_categorize, output_field, categories, max_workers
        )
        
        # Show preview
        print("\nCategorization completed. Here's a preview:")
        categorized_results = [r for r in results if r["status"] == "categorized"]
        for result in categorized_results[:3]:  # Show first 3
            print(f"UUID: {result['uuid']} -> Category: {result['category']}")
        
        # Ask for confirmation
        proceed = input(f"\nApply updates to {len(categorized_results)} documents? (y/N): ").strip().lower()
        if proceed == 'y':
            print("Updating documents...")
            update_stats = categorizer.update_documents(results, output_field)
            categorizer.print_summary(field_check, results, update_stats)
        else:
            print("Updates cancelled.")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        print(f"Error: {e}")
    finally:
        categorizer.client.close()

if __name__ == "__main__":
    asyncio.run(main())
