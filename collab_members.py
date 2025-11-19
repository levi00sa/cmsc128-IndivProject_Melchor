#collab_members.py

import sqlite3
import os

def initialize_db():
    # Check if database file exists and is corrupted, delete if so
    db_file = 'collab_members.db'
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

    #create collab_members table
    c.execute('''
            CREATE TABLE IF NOT EXISTS collab_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collab_list_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(collab_list_id, user_id),
                FOREIGN KEY (collab_list_id) REFERENCES collab_lists(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('collab_members.db')
    conn.row_factory = sqlite3.Row
    return conn

def add_collab_member(collab_list_id, user_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO collab_members (collab_list_id, user_id) VALUES (?, ?)', (collab_list_id, user_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # User is already a member
        conn.close()
        return False

def get_collab_members(collab_list_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM collab_members WHERE collab_list_id = ?', (collab_list_id,))
    collab_members = c.fetchall()
    conn.close()
    return collab_members

def get_collab_lists_for_user(user_id):
    """Get all collaborative lists that a user is a member of (including owned lists)"""
    conn = get_db_connection()
    c = conn.cursor()
    # Get lists where user is a member
    c.execute('''
        SELECT DISTINCT cm.collab_list_id 
        FROM collab_members cm 
        WHERE cm.user_id = ?
    ''', (user_id,))
    member_list_ids = [row[0] for row in c.fetchall()]
    conn.close()
    return member_list_ids

def remove_collab_member(collab_list_id, user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM collab_members WHERE collab_list_id = ? AND user_id = ?', (collab_list_id, user_id))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def is_user_member(collab_list_id, user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM collab_members WHERE collab_list_id = ? AND user_id = ?', (collab_list_id, user_id))
    member = c.fetchone()
    conn.close()
    return member is not None

def count_collab_members(collab_list_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as total FROM collab_members WHERE collab_list_id = ?', (collab_list_id,))
    result = c.fetchone()
    conn.close()
    return result['total'] if result else 0