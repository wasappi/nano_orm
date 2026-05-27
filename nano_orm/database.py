import sqlite3

def get_connection():
    connection = sqlite3.connect(_db_name)
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection

def init_db(db_name):
    global _db_name
    _db_name = db_name

