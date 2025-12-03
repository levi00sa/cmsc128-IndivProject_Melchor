#collab_members.py

import sqlite3
import json
import os

def initialize_db():
    pass

def get_db_connection():
    conn = sqlite3.connect('collab_lists.db')
    conn.row_factory = sqlite3.Row
    return conn

def add_member_to_list(list_id, user_id):
    """Add a member to collab list's members array"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT members FROM collab_lists WHERE id = ?', (list_id,))
    result = c.fetchone()
    
    if result:
        members = json.loads(result['members']) if result['members'] else []
        if user_id not in members:
            members.append(user_id)
        
        c.execute('UPDATE collab_lists SET members = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                  (json.dumps(members), list_id))
        conn.commit()
    
    conn.close()
    return result is not None

def remove_member_from_list(list_id, user_id):
    """Remove a member from collab list's members array"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT members FROM collab_lists WHERE id = ?', (list_id,))
    result = c.fetchone()
    
    if result:
        members = json.loads(result['members']) if result['members'] else []
        members = [m for m in members if m != user_id]
        
        c.execute('UPDATE collab_lists SET members = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                  (json.dumps(members), list_id))
        conn.commit()
    
    conn.close()
    return result is not None

def get_list_members(list_id):
    """Get all members from a collab list"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT members FROM collab_lists WHERE id = ?', (list_id,))
    result = c.fetchone()
    conn.close()
    
    return json.loads(result['members']) if result and result['members'] else []

def is_member_in_list(list_id, user_id):
    """Check if user is a member of the list"""
    members = get_list_members(list_id)
    return user_id in members

def is_user_owner(list_id, user_id):
    """Check if user is the owner of a list (first member is owner)"""
    members = get_list_members(list_id)
    return len(members) > 0 and members[0] == user_id

def count_collab_members(list_id):
    """Count total members in a list"""
    members = get_list_members(list_id)
    return len(members)

# Legacy function names for backward compatibility
def add_collab_member(collab_list_id, user_id, role='member'):
    """Legacy function - adds member to list (role parameter ignored with JSON storage)"""
    return add_member_to_list(collab_list_id, user_id)

def get_collab_members(collab_list_id):
    """Legacy function - returns member IDs as list"""
    return get_list_members(collab_list_id)

def get_collab_lists_for_user(user_id):
    """Get all collaborative lists that a user is a member of"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, members FROM collab_lists')
    all_lists = c.fetchall()
    conn.close()
    
    user_lists = []
    for row in all_lists:
        members = json.loads(row['members']) if row['members'] else []
        if user_id in members:
            user_lists.append(row['id'])
    
    return user_lists

def remove_collab_member(collab_list_id, user_id):
    """Legacy function - removes member from list"""
    return remove_member_from_list(collab_list_id, user_id)

def is_user_member(collab_list_id, user_id):
    """Check if user is a member of the list"""
    return is_member_in_list(collab_list_id, user_id)