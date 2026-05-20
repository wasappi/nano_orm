import sqlite3
#from pathlib import Path

DB_NAME = "nano_orm_v1.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def initialize_db():
    connection = get_connection()
    connection.close()

