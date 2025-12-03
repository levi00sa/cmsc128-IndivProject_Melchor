#collab_lists.py

import sqlite3
import os
import json

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

    # Create collab_lists table with members as JSON array
    c.execute('''
            CREATE TABLE IF NOT EXISTS collab_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                members TEXT DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    
    # Create empty members array with owner_id as first member
    initial_members = json.dumps([owner_id])
    c.execute('INSERT INTO collab_lists (name, members) VALUES (?, ?)', (name, initial_members))
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
    c.execute('SELECT * FROM collab_lists ORDER BY created_at DESC')
    all_lists = c.fetchall()
    conn.close()

    # Filter lists where the requester is the owner (first member in members array)
    owned_lists = []
    for collab_list in all_lists:
        members = json.loads(collab_list['members']) if collab_list['members'] else []
        if members and members[0] == owner_id:
            owned_lists.append(collab_list)

    return owned_lists

def get_list_owner_id(list_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT members FROM collab_lists WHERE id = ?', (list_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        members = json.loads(result['members']) if result['members'] else []
        return members[0] if members else None
    return None

def edit_collab_list(list_id, new_name, owner_id):
    owner = get_list_owner_id(list_id)
    if owner != owner_id:
        return False

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("UPDATE collab_lists SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_name, list_id))
    updated = c.rowcount > 0

    conn.commit()
    conn.close()

    return updated

def delete_collab_list(list_id, owner_id):
    owner = get_list_owner_id(list_id)
    if owner != owner_id:
        return False

    # Delete tasks for this list (safe try)
    try:
        tasks_conn = sqlite3.connect("tasks.db")
        tc = tasks_conn.cursor()
        tc.execute("DELETE FROM tasks WHERE collab_list_id = ?", (list_id,))
        tasks_conn.commit()
        tasks_conn.close()
    except Exception as e:
        print(f"[WARNING] Failed to delete tasks for list {list_id}: {e}")

    # Delete list itself
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM collab_lists WHERE id = ?", (list_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()

    return deleted