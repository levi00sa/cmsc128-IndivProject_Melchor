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
                role TEXT NOT NULL DEFAULT 'member',
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

def add_collab_member(collab_list_id, user_id, role='member'):
    """Add a member with a specific role (default: 'member')"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO collab_members (collab_list_id, user_id, role) VALUES (?, ?, ?)', 
                  (collab_list_id, user_id, role))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
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

def is_user_owner(collab_list_id, user_id):
    """Check if user is the owner of a list"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM collab_members 
        WHERE collab_list_id = ? AND user_id = ? AND role = 'owner'
    ''', (collab_list_id, user_id))
    is_owner = c.fetchone() is not None
    conn.close()
    return is_owner

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

def get_user_role(collab_list_id, user_id):
    """Get a user's role in a list"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT role FROM collab_members 
        WHERE collab_list_id = ? AND user_id = ?
    ''', (collab_list_id, user_id))
    result = c.fetchone()
    conn.close()
    return result['role'] if result else None

def has_permission(collab_list_id, user_id, required_role='member'):
    """Check if user has at least the required permission level"""
    role_hierarchy = {'owner': 3, 'editor': 2, 'member': 1}
    user_role = get_user_role(collab_list_id, user_id)
    
    if not user_role:
        return False
    
    return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)

def count_collab_members(collab_list_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as total FROM collab_members WHERE collab_list_id = ?', (collab_list_id,))
    result = c.fetchone()
    conn.close()
    return result['total'] if result else 0