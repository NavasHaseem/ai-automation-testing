#!/usr/bin/env python3
"""
Script to delete all vectors from a Pinecone namespace.
"""
import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

from Backend.utils.pinecone_store import delete_namespace

def main():
    namespace = "mongodb-files"
    
    if len(sys.argv) > 1:
        namespace = sys.argv[1]
    
    print(f"🗑️  Deleting all vectors from namespace: {namespace}")
    
    try:
        result = delete_namespace(namespace)
        print(f"✅ Successfully deleted vectors from '{namespace}'")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"❌ Error deleting namespace: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
