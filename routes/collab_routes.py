# routes/collab_routes.py
from flask import Blueprint, request, jsonify, session
from collab_lists import (
    create_collab_list, get_collab_list_by_id, get_collab_lists_by_owner, delete_collab_list
)
from collab_members import (
    add_collab_member, get_collab_members, get_collab_lists_for_user, 
    is_user_member, remove_collab_member
)
from database import get_db_connection
from routes.auth_routes import login_required
from tasks import get_tasks_for_collab_list

collab_bp = Blueprint('collab_bp', __name__)

# Get all collaborative lists that the user owns or is a member of
@collab_bp.route('/collab_lists', methods=['GET'])
@login_required
def get_user_collab_lists():
    user_id = session.get('user_id')                                        #Get current logged in user

    owned_lists = get_collab_lists_by_owner(user_id)                        # Fetch lists owned by current logged in user

    member_list_ids = get_collab_lists_for_user(user_id)                    # Fetch lists where current logged in user is a member
    member_lists = []                                                       #get lists where user is a member
    for list_id in member_list_ids:                                         # For each list id in member_list_ids, fetch full list data 
        collab_list = get_collab_list_by_id(list_id)                            # to fetch list by id
        if collab_list and collab_list['owner_id'] != user_id:                  
            member_lists.append(collab_list)                                    # Add list to member lists
    
    all_lists = []                                                            #add lists the user owns
    for list_item in owned_lists:                                            # For each list in owned_lists, add to all_lists
        all_lists.append({
            'id': list_item['id'],
            'name': list_item['name'],
            'owner_id': list_item['owner_id'],
            'is_owner': True,
            'created_at': list_item['created_at']
        })
    
    for list_item in member_lists:                                           # For each list in member_lists, add to all_lists      
        all_lists.append({
            'id': list_item['id'],
            'name': list_item['name'],
            'owner_id': list_item['owner_id'],
            'is_owner': False,
            'created_at': list_item['created_at']
        })
    
    return jsonify({'success': True, 'lists': all_lists})

# Create a new collaborative list
@collab_bp.route('/collab_lists', methods=['POST'])
@login_required
def create_list():
    user_id = session.get('user_id')                                        # Get current logged in user
    data = request.get_json()                                               
    
    name = data.get('name', '').strip()                                     # Get list name from request body
    if not name:                                                            # If list name is not provided, return error
        return jsonify({'success': False, 'message': 'List name is required'}), 400
    
    try:
        collab_list = create_collab_list(user_id, name)

        # add owner as member automatically
        add_collab_member(collab_list['id'], user_id)
        return jsonify({
            'success': True,
            'message': 'Collaborative list created successfully',
            'list': {
                'id': collab_list['id'],
                'name': collab_list['name'],
                'owner_id': collab_list['owner_id'],
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
    collab_list = get_collab_list_by_id(list_id)
    
    if not collab_list:
        return jsonify({'success': False, 'message': 'List not found'}), 404
    
    # Check if user has access either as owner or member of collab list
    is_owner = collab_list['owner_id'] == user_id
    is_member = is_user_member(list_id, user_id) if not is_owner else True
    
    if not is_owner and not is_member:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Get owner info
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, name, email FROM users WHERE id = ?', (collab_list['owner_id'],))
    owner = c.fetchone()
    conn.close()
    
    # Get members
    members = get_collab_members(list_id)
    member_list = []
    
    # Add owner first
    if owner:
        member_list.append({
            'id': owner['id'],
            'username': owner['username'],
            'name': owner['name'],
            'email': owner['email'],
            'is_owner': True
        })
    
    # Add other members
    for member in members:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT id, username, name, email FROM users WHERE id = ?', (member['user_id'],))
        user = c.fetchone()
        conn.close()
        if user:
            member_list.append({
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'email': user['email'],
                'is_owner': False
            })
    
    return jsonify({
        'success': True,
        'list': {
            'id': collab_list['id'],
            'name': collab_list['name'],
            'owner_id': collab_list['owner_id'],
            'is_owner': is_owner,
            'members': member_list,
            'created_at': collab_list['created_at']
        }
    })

#Delete a collaborative list but only owner of that list can delete
@collab_bp.route('/collab_lists/<int:list_id>', methods=['DELETE'])
@login_required
def delete_list(list_id):
    user_id = session.get('user_id')
    collab_list = get_collab_list_by_id(list_id)
    
    #check if list is there
    if not collab_list:
        return jsonify({'success': False, 'message': 'List not found'}), 404
    
    #check if current user is the owner
    if collab_list['owner_id'] != user_id:
        return jsonify({'success': False, 'message': 'Only the owner can delete the list'}), 403
    
    try:
        deleted = delete_collab_list(list_id, user_id) #store deleted list
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
    
    collab_list = get_collab_list_by_id(list_id)
    if not collab_list:
        return jsonify({'success': False, 'message': 'List not found'}), 404
    
    # Check if user is owner or member
    is_owner = collab_list['owner_id'] == user_id
    is_member = is_user_member(list_id, user_id) if not is_owner else True
    
    if not is_owner and not is_member:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
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
    collab_list = get_collab_list_by_id(list_id)
    
    #check if list is there
    if not collab_list:
        return jsonify({'success': False, 'message': 'List not found'}), 404
    
    # check if current user is owner
    if collab_list['owner_id'] != user_id:
        return jsonify({'success': False, 'message': 'Only the owner can remove members'}), 403
    
    #check if current user is removing themself
    if member_id == user_id:
        return jsonify({'success': False, 'message': 'Owner cannot remove themselves'}), 400
    
    #store removed member
    #check if member removal is successful, else error
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
    collab_list = get_collab_list_by_id(list_id)
    
    if not collab_list:
        return jsonify({'success': False, 'message': 'List not found'}), 404
    
    # Check if user has access
    is_owner = collab_list['owner_id'] == user_id
    is_member = is_user_member(list_id, user_id) if not is_owner else True
    
    if not is_owner and not is_member:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
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

