# routes/collab_routes.py
from flask import Blueprint, request, jsonify, session
from collab_lists import (
    create_collab_list, get_collab_list_by_id, get_collab_lists_by_owner, 
    delete_collab_list, get_list_owner_id, edit_collab_list
)
from collab_members import (
    add_collab_member, get_collab_members, get_collab_lists_for_user,
    is_user_member, remove_collab_member, count_collab_members, is_user_owner
)
from database import get_db_connection
from routes.auth_routes import login_required
from tasks import get_tasks_for_collab_list

collab_bp = Blueprint('collab_bp', __name__)


def _ensure_list_access(list_id, user_id, owner_only=False):
    """Helper to check if user has access to a list"""
    collab_list = get_collab_list_by_id(list_id)
    if not collab_list:
        return None, False, (jsonify({'success': False, 'message': 'List not found'}), 404)

    # Get owner_id from collab_members table
    owner_id = get_list_owner_id(list_id)
    is_owner = owner_id == user_id
    
    if owner_only and not is_owner:
        return None, False, (jsonify({'success': False, 'message': 'Only the owner can perform this action'}), 403)

    if not is_owner:
        if not is_user_member(list_id, user_id):
            return None, False, (jsonify({'success': False, 'message': 'Access denied'}), 403)

    return collab_list, is_owner, None


def _fetch_owner_names(owner_ids):
    """Fetch owner names for given owner IDs"""
    if not owner_ids:
        return {}
    placeholders = ','.join(['?'] * len(owner_ids))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f'SELECT id, name FROM users WHERE id IN ({placeholders})', tuple(owner_ids))
    owners = {row['id']: row['name'] for row in c.fetchall()}
    conn.close()
    return owners

# Get all collaborative lists that the user owns or is a member of
@collab_bp.route('/collab_lists', methods=['GET'])
@login_required
def get_user_collab_lists():
    user_id = session.get('user_id')

    owned_lists = get_collab_lists_by_owner(user_id)

    member_list_ids = get_collab_lists_for_user(user_id)
    member_lists = []
    
    for list_id in member_list_ids:
        collab_list = get_collab_list_by_id(list_id)
        if collab_list:
            owner_id = get_list_owner_id(list_id)
            if owner_id != user_id:  # Exclude lists where user is owner (already in owned_lists)
                member_lists.append(collab_list)
    
    # Get all unique owner IDs from member_lists
    owner_ids = {get_list_owner_id(l['id']) for l in member_lists}
    owner_name_lookup = _fetch_owner_names(owner_ids)

    all_lists = []
    
    # Add owned lists
    for list_item in owned_lists:
        all_lists.append({
            'id': list_item['id'],
            'name': list_item['name'],
            'owner_id': user_id,
            'owner_name': session.get('name', 'You'),
            'is_owner': True,
            'member_count': count_collab_members(list_item['id']),
            'created_at': list_item['created_at']
        })

    # Add member lists
    for list_item in member_lists:
        owner_id = get_list_owner_id(list_item['id'])
        all_lists.append({
            'id': list_item['id'],
            'name': list_item['name'],
            'owner_id': owner_id,
            'owner_name': owner_name_lookup.get(owner_id, 'Owner'),
            'is_owner': False,
            'member_count': count_collab_members(list_item['id']),
            'created_at': list_item['created_at']
        })
    
    # Sort with owned lists first, then alphabetically
    all_lists.sort(key=lambda l: (0 if l['is_owner'] else 1, l['name'].lower()))
    
    return jsonify({'success': True, 'lists': all_lists})

# Create a new collaborative list
@collab_bp.route('/collab_lists', methods=['POST'])
@login_required
def create_list():
    user_id = session.get('user_id')
    data = request.get_json()
    
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'List name is required'}), 400
    
    try:
        collab_list = create_collab_list(user_id, name)
        
        return jsonify({
            'success': True,
            'message': 'Collaborative list created successfully',
            'list': {
                'id': collab_list['id'],
                'name': collab_list['name'],
                'owner_id': user_id,
                'created_at': collab_list['created_at']
            }
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error creating list: {str(e)}'}), 500

# Get a specific collaborative list
@collab_bp.route('/collab_lists/<int:list_id>', methods=['GET'])
@login_required
def get_list(list_id):
    user_id = session.get('user_id')
    collab_list, is_owner, error = _ensure_list_access(list_id, user_id)
    if error:
        return error
    
    owner_id = get_list_owner_id(list_id)
    
    # Get owner info
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, name, email FROM users WHERE id = ?', (owner_id,))
    owner = c.fetchone()
    
    # Get members
    members = get_collab_members(list_id)
    member_ids = members  # members is now a list of user IDs, not database rows
    member_list = []

    if member_ids:
        placeholders = ','.join(['?'] * len(member_ids))
        c.execute(f'''
            SELECT id, username, name, email
            FROM users
            WHERE id IN ({placeholders})
        ''', tuple(member_ids))
        users_by_id = {row['id']: row for row in c.fetchall()}
        for user_id_iter in member_ids:
            user = users_by_id.get(user_id_iter)
            if user:
                member_list.append({
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'email': user['email'],
                    'is_owner': user['id'] == owner_id
                })
    conn.close()
    
    # Ensure owner appears first
    member_list.sort(key=lambda m: (0 if m['is_owner'] else 1, m['name'].lower()))
    
    return jsonify({
        'success': True,
        'list': {
            'id': collab_list['id'],
            'name': collab_list['name'],
            'owner_id': owner_id,
            'is_owner': is_owner,
            'members': member_list,
            'created_at': collab_list['created_at']
        }
    })

# Edit a collaborative list (only owner can edit)
@collab_bp.route('/collab_lists/<int:list_id>', methods=['PUT'])
@login_required
def edit_list(list_id):
    user_id = session.get('user_id')
    collab_list, _, error = _ensure_list_access(list_id, user_id, owner_only=True)
    if error:
        return error
    
    data = request.get_json()
    new_name = data.get('name', '').strip()
    
    if not new_name:
        return jsonify({'success': False, 'message': 'List name is required'}), 400
    
    try:
        updated = edit_collab_list(list_id, new_name, user_id)
        if updated:
            return jsonify({
                'success': True,
                'message': 'List name updated successfully',
                'list': {
                    'id': list_id,
                    'name': new_name
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to update list'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating list: {str(e)}'}), 500

#Delete a collaborative list but only owner of that list can delete
@collab_bp.route('/collab_lists/<int:list_id>', methods=['DELETE'])
@login_required
def delete_list(list_id):
    user_id = session.get('user_id')
    collab_list, _, error = _ensure_list_access(list_id, user_id, owner_only=True)
    if error:
        return error
    
    try:
        deleted = delete_collab_list(list_id, user_id)
        if deleted:
            return jsonify({'success': True, 'message': 'List deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete list'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting list: {str(e)}'}), 500

#Add member to a collaborative list
@collab_bp.route('/collab_lists/<int:list_id>/members', methods=['POST'])
@login_required
def add_member(list_id):
    user_id = session.get('user_id')
    data = request.get_json()
    
    collab_list, is_owner, error = _ensure_list_access(list_id, user_id)
    if error:
        return error
    
    # Get user to add by username or email
    username_or_email = data.get('username_or_email', '').strip()
    if not username_or_email:
        return jsonify({'success': False, 'message': 'Username or email is required'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username_or_email, username_or_email))
    user_to_add = c.fetchone()
    conn.close()
    
    if not user_to_add:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    if user_to_add['id'] == user_id:
        return jsonify({'success': False, 'message': 'You cannot add yourself'}), 400
    
    # Add member
    added = add_collab_member(list_id, user_to_add['id'])
    if added:
        return jsonify({
            'success': True,
            'message': f'User {user_to_add["username"]} added successfully',
            'user': {
                'id': user_to_add['id'],
                'username': user_to_add['username'],
                'name': user_to_add['name'],
                'email': user_to_add['email']
            }
        })
    else:
        return jsonify({'success': False, 'message': 'User is already a member'}), 400

#remove member from collab list but only owner can do that
@collab_bp.route('/collab_lists/<int:list_id>/members/<int:member_id>', methods=['DELETE'])
@login_required
def remove_member(list_id, member_id):
    user_id = session.get('user_id')
    collab_list, _, error = _ensure_list_access(list_id, user_id, owner_only=True)
    if error:
        return error
    
    #check if current user is removing themself
    if member_id == user_id:
        return jsonify({'success': False, 'message': 'Owner cannot remove themselves'}), 400
    
    try:
        removed = remove_collab_member(list_id, member_id)
        if removed:
            return jsonify({'success': True, 'message': 'Member removed successfully'})
        else:
            return jsonify({'success': False, 'message': 'Member not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error removing member: {str(e)}'}), 500

#Get all tasks for a collab list
@collab_bp.route('/collab_lists/<int:list_id>/tasks', methods=['GET'])
@login_required
def get_list_tasks(list_id):
    user_id = session.get('user_id')
    collab_list, _, error = _ensure_list_access(list_id, user_id)
    if error:
        return error
    
    status = request.args.get('status')
    priority = request.args.get('priority')
    
    tasks = get_tasks_for_collab_list(list_id, status=status, priority=priority)
    
    tasks_list = []
    for task in tasks:
        tasks_list.append({
            'id': task['id'],
            'title': task['title'],
            'description': task['description'] or '',
            'priority': task['priority'],
            'status': task['status'],
            'due_date': task['due_date'] or '',
            'created_at': task['created_at'],
            'updated_at': task['updated_at'],
            'user_id': task['user_id'],
            'collab_list_id': task['collab_list_id']
        })
    
    return jsonify({'success': True, 'tasks': tasks_list})