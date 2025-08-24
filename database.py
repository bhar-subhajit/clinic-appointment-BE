# database.py
import sqlite3
import os
from datetime import datetime

def init_db():
    """Initialize the database with appointments table"""
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    
    # Create appointments table
    c.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        service TEXT,
        message TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        contacted BOOLEAN DEFAULT FALSE,
        contact_notes TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect('appointments.db')
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

# Initialize the database when this module is imported
init_db()