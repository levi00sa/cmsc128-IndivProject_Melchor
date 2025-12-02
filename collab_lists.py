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

    # Create collab_lists table WITHOUT owner_id and without trailing comma
    c.execute('''
            CREATE TABLE IF NOT EXISTS collab_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    
    # Create the list without owner_id - FIXED: removed owner_id, fixed VALUES syntax
    c.execute('INSERT INTO collab_lists (name) VALUES (?)', (name,))
    list_id = c.lastrowid
    conn.commit()
    
    c.execute('SELECT * FROM collab_lists WHERE id = ?', (list_id,))
    collab_list = c.fetchone()
    conn.close()
    
    # Add creator as owner in collab_members
    from collab_members import add_collab_member
    add_collab_member(list_id, owner_id, role='owner')
    
    return collab_list

def get_collab_list_by_id(list_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM collab_lists WHERE id = ?', (list_id,))
    collab_list = c.fetchone()
    conn.close()
    return collab_list

def get_collab_lists_by_owner(owner_id):
    # Need to query across two databases - use direct connection to collab_members
    from collab_members import get_db_connection as get_members_conn
    
    # First, get list IDs where user is owner from collab_members
    members_conn = get_members_conn()
    mc = members_conn.cursor()
    mc.execute('''
        SELECT collab_list_id 
        FROM collab_members 
        WHERE user_id = ? AND role = 'owner'
    ''', (owner_id,))
    list_ids = [row[0] for row in mc.fetchall()]
    members_conn.close()
    
    if not list_ids:
        return []
    
    # Now get the actual list data from collab_lists
    conn = get_db_connection()
    c = conn.cursor()
    placeholders = ','.join(['?'] * len(list_ids))
    c.execute(f'''
        SELECT * FROM collab_lists 
        WHERE id IN ({placeholders})
        ORDER BY created_at DESC
    ''', tuple(list_ids))
    collab_lists = c.fetchall()
    conn.close()
    return collab_lists

def get_list_owner_id(list_id):
    from collab_members import get_db_connection as get_members_conn
    conn = get_members_conn()
    c = conn.cursor()
    c.execute('''
        SELECT user_id FROM collab_members 
        WHERE collab_list_id = ? AND role = 'owner'
        LIMIT 1
    ''', (list_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def edit_collab_list(list_id, new_name, owner_id):
    from collab_members import is_user_owner

    if not is_user_owner(list_id, owner_id):
        return False

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("UPDATE collab_lists SET name = ? WHERE id = ?", (new_name, list_id))
    updated = c.rowcount > 0

    conn.commit()
    conn.close()

    return updated

def delete_collab_list(list_id, owner_id):
    from collab_members import is_user_owner, get_db_connection as get_members_conn

    if not is_user_owner(list_id, owner_id):
        return False

    # Delete members first
    members_conn = get_members_conn()
    mc = members_conn.cursor()
    mc.execute("DELETE FROM collab_members WHERE collab_list_id = ?", (list_id,))
    members_conn.commit()
    members_conn.close()

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