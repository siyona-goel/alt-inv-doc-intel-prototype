from app.db.mongo import get_db

db = get_db()
print("Collections:", db.list_collection_names())
