#tasks.py

import sqlite3
from datetime import datetime

def initialize_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    # Create tasks table
    c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'pending',
        due_date TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        collab_list_id INTEGER,
        archived INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (collab_list_id) REFERENCES collab_lists(id)
    )
    ''')
    # Add archived column if it doesn't exist (for existing databases)
    try:
        c.execute('ALTER TABLE tasks ADD COLUMN archived INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('tasks.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_task(user_id, title, description=None, priority='Medium', status='pending', due_date=None, collab_list_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO tasks (user_id, title, description, priority, status, due_date, collab_list_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, title, description, priority, status, due_date, collab_list_id))
    task_id = c.lastrowid
    conn.commit()
    c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = c.fetchone()
    conn.close()
    return task

def get_tasks(user_id, status=None, priority=None, collab_list_id=None, include_archived=False):
    conn = get_db_connection()
    c = conn.cursor()
    
    if collab_list_id:
        # Get tasks for a specific collaborative list
        query = 'SELECT * FROM tasks WHERE collab_list_id = ?'
        params = [collab_list_id]
    else:
        # Get personal tasks (where collab_list_id is NULL)
        query = 'SELECT * FROM tasks WHERE user_id = ? AND collab_list_id IS NULL'
        params = [user_id]
    
    if status:
        query += ' AND status = ?'
        params.append(status)
    
    if priority:
        query += ' AND priority = ?'
        params.append(priority)
    
    # Filter out archived tasks unless explicitly requested
    if not include_archived:
        query += ' AND (archived IS NULL OR archived = 0)'
    
    query += ' ORDER BY created_at DESC'
    
    c.execute(query, tuple(params))
    tasks = c.fetchall()
    conn.close()
    return tasks

def get_tasks_for_collab_list(collab_list_id, status=None, priority=None, include_archived=False):
    """Get all tasks for a collaborative list"""
    return get_tasks(None, status=status, priority=priority, collab_list_id=collab_list_id, include_archived=include_archived)

def get_task_by_id(task_id, user_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = c.fetchone()
    conn.close()
    return task

def update_task(task_id, user_id=None, title=None, description=None, priority=None, status=None, due_date=None, archived=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    updates = []
    params = []
    
    if title is not None:
        updates.append('title = ?')
        params.append(title)
    if description is not None:
        updates.append('description = ?')
        params.append(description)
    if priority is not None:
        updates.append('priority = ?')
        params.append(priority)
    if status is not None:
        updates.append('status = ?')
        params.append(status)
    if due_date is not None:
        updates.append('due_date = ?')
        params.append(due_date)
    if archived is not None:
        updates.append('archived = ?')
        params.append(1 if archived else 0)
    
    if not updates:
        conn.close()
        return None
    
    updates.append('updated_at = ?')
    params.append(datetime.now().isoformat())
    params.append(task_id)
    
    if user_id:
        query = f'UPDATE tasks SET {", ".join(updates)} WHERE id = ? AND (user_id = ? OR collab_list_id IS NOT NULL)'
        params.append(user_id)
    else:
        query = f'UPDATE tasks SET {", ".join(updates)} WHERE id = ?'
    
    c.execute(query, tuple(params))
    conn.commit()
    
    c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = c.fetchone()
    conn.close()
    return task

def archive_task(task_id, user_id=None):
    """Archive a task"""
    return update_task(task_id, user_id=user_id, archived=True)

def unarchive_task(task_id, user_id=None):
    """Unarchive a task"""
    return update_task(task_id, user_id=user_id, archived=False)

def delete_task(task_id, user_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    if user_id:
        # Allow deletion if user owns the task or it's in a collab list they have access to
        c.execute('DELETE FROM tasks WHERE id = ? AND (user_id = ? OR collab_list_id IS NOT NULL)', (task_id, user_id))
    else:
        c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def search_tasks(user_id, search_term, include_archived=False):
    conn = get_db_connection()
    c = conn.cursor()
    query = '''
        SELECT * FROM tasks 
        WHERE user_id = ? 
        AND (title LIKE ? OR description LIKE ?)
    '''
    if not include_archived:
        query += ' AND (archived IS NULL OR archived = 0)'
    query += ' ORDER BY created_at DESC'
    c.execute(query, (user_id, f'%{search_term}%', f'%{search_term}%'))
    tasks = c.fetchall()
    conn.close()
    return tasks
