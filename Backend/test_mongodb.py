"""
Test MongoDB connection
Run this to verify your MongoDB setup is working correctly.
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

load_dotenv()

def test_mongodb_connection():
    """Test MongoDB connection and database operations."""
    
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    mongodb_db = os.getenv("MONGODB_DB", "filedb")
    
    print("🔍 Testing MongoDB Connection...")
    print(f"   URI: {mongodb_uri}")
    print(f"   Database: {mongodb_db}")
    print("-" * 60)
    
    try:
        # Create client
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB Connection: SUCCESS")
        
        # Get database
        db = client[mongodb_db]
        print(f"✅ Database '{mongodb_db}': Accessible")
        
        # List collections
        collections = db.list_collection_names()
        print(f"✅ Collections found: {len(collections)}")
        if collections:
            for col in collections:
                count = db[col].count_documents({})
                print(f"   - {col}: {count} documents")
        else:
            print("   (No collections yet - this is normal for new setup)")
        
        # Test GridFS collections
        gridfs_files = "fs.files" in collections
        gridfs_chunks = "fs.chunks" in collections
        
        if gridfs_files or gridfs_chunks:
            print(f"✅ GridFS: Configured")
            if gridfs_files:
                file_count = db["fs.files"].count_documents({})
                print(f"   - Files stored: {file_count}")
        else:
            print("ℹ️  GridFS: Not initialized yet (will be created on first upload)")
        
        # Server info
        server_info = client.server_info()
        print(f"✅ MongoDB Version: {server_info['version']}")
        
        print("-" * 60)
        print("🎉 MongoDB is ready for the AI Automation Testing app!")
        
        client.close()
        return True
        
    except ConnectionFailure:
        print("❌ Connection Failed: Cannot reach MongoDB server")
        print("   Make sure MongoDB is running on localhost:27017")
        print("   Run: mongod --version")
        return False
        
    except ServerSelectionTimeoutError:
        print("❌ Connection Timeout: MongoDB server not responding")
        print("   Check if MongoDB service is started:")
        print("   Windows: net start MongoDB")
        print("   Or run: mongod --dbpath=<path_to_data>")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}")
        print(f"   {str(e)}")
        return False


if __name__ == "__main__":
    test_mongodb_connection()
