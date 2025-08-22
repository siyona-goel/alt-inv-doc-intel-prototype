from pymongo import MongoClient
import os

# later move this to environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "doc_intel")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def get_db():
    return db
