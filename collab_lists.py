#collab_lists.py

import sqlite3
import os

def initialize_db():
    # Check if database file exists and is corrupted, delete if so
    db_file = 'collab_lists.db'
    if os.path.exists(db_file):
        try:
            # Try to open and verify the database
            test_conn = sqlite3.connect(db_file)
            test_conn.execute('SELECT 1')
            test_conn.close()
        except (sqlite3.DatabaseError, sqlite3.Error):
            # Database is corrupted, delete it
            os.remove(db_file)
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # Create collab_lists table
    c.execute('''
            CREATE TABLE IF NOT EXISTS collab_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('collab_lists.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_collab_list(owner_id, name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO collab_lists (owner_id, name) VALUES (?, ?)', (owner_id, name))
    list_id = c.lastrowid
    conn.commit()
    c.execute('SELECT * FROM collab_lists WHERE id = ?', (list_id,))
    collab_list = c.fetchone()
    conn.close()
    return collab_list

def get_collab_list_by_id(list_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM collab_lists WHERE id = ?', (list_id,))
    collab_list = c.fetchone()
    conn.close()
    return collab_list

def get_collab_lists_by_owner(owner_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM collab_lists WHERE owner_id = ? ORDER BY created_at DESC', (owner_id,))
    collab_lists = c.fetchall()
    conn.close()
    return collab_lists

def delete_collab_list(list_id, owner_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM collab_lists WHERE id = ? AND owner_id = ?', (list_id, owner_id))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted