# routes/task_routes.py
from flask import Blueprint, request, jsonify, session, render_template
from tasks import (
    initialize_db, create_task, get_tasks, get_task_by_id,
    update_task, delete_task, search_tasks, archive_task, unarchive_task
)
from routes.auth_routes import login_required
from routes.auth_routes import nocache

task_bp = Blueprint('task_bp', __name__)

initialize_db()

#Get all tasks for the logged-in user (personal or collaborative)
@task_bp.route('/tasks', methods=['GET'])
@login_required
@nocache
def get_user_tasks():
    #get all values
    user_id = session.get('user_id')
    status = request.args.get('status')
    priority = request.args.get('priority')
    search = request.args.get('search')
    collab_list_id = request.args.get('collab_list_id', type=int)
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    archived_only = request.args.get('archived_only', 'false').lower() == 'true'
    
    if collab_list_id:
        # Get tasks for a specific collaborative list
        from collab_members import is_user_owner, is_user_member
        from collab_lists import get_collab_list_by_id
        
        collab_list = get_collab_list_by_id(collab_list_id)
        if not collab_list:
            return jsonify({'success': False, 'message': 'List not found'}), 404
        
        # Check if user has access (is owner or member)
        if not is_user_owner(collab_list_id, user_id) and not is_user_member(collab_list_id, user_id):
            return jsonify({'error': 'Unauthorized'}), 403
                
        from tasks import get_tasks_for_collab_list
        if archived_only:
            # Get only archived tasks
            tasks = get_tasks_for_collab_list(collab_list_id, status=status, priority=priority, include_archived=True)
            tasks = [t for t in tasks if (t['archived'] or 0) == 1]
        else:
            tasks = get_tasks_for_collab_list(collab_list_id, status=status, priority=priority, include_archived=include_archived)
    else:
        # Get personal tasks
        if archived_only:
            # Get only archived tasks
            tasks = get_tasks(user_id, status=status, priority=priority, include_archived=True)
            tasks = [t for t in tasks if (t['archived'] or 0) == 1]
        elif search:
            tasks = search_tasks(user_id, search)
        else:
            tasks = get_tasks(user_id, status=status, priority=priority, include_archived=include_archived)
    
    # Convert Row objects to dictionaries
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
            'collab_list_id': task['collab_list_id'],
            'archived': task['archived'] if task['archived'] is not None else 0
        })
    
    return jsonify({'success': True, 'tasks': tasks_list})

#Create a new task (personal or collaborative)
@task_bp.route('/tasks', methods=['POST'])
@login_required
@nocache
def add_task():
    user_id = session.get('user_id')
    data = request.get_json()
    
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'success': False, 'message': 'Task title is required'}), 400
    
    description = data.get('description', '').strip() or None
    priority = data.get('priority', 'Medium')
    status = data.get('status', 'pending')
    due_date = data.get('due_date') or None
    collab_list_id = data.get('collab_list_id')
    
    #convert collab_list_id to integer
    if collab_list_id is not None:
        try:
            collab_list_id = int(collab_list_id)
        except (ValueError, TypeError):
            collab_list_id = None
    
    # If collab_list_id is provided, verify user has access
    if collab_list_id:
        from collab_members import is_user_member, is_user_owner
        from collab_lists import get_collab_list_by_id
        
        collab_list = get_collab_list_by_id(collab_list_id)
        if not collab_list:
            return jsonify({'success': False, 'message': 'List not found'}), 404
        
        # Check if user has access (is owner or member)
        if not is_user_owner(collab_list_id, user_id) and not is_user_member(collab_list_id, user_id):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        task = create_task(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            status=status,
            due_date=due_date,
            collab_list_id=collab_list_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Task created successfully',
            'task': {
                'id': task['id'],
                'title': task['title'],
                'description': task['description'] or '',
                'priority': task['priority'],
                'status': task['status'],
                'due_date': task['due_date'] or '',
                'created_at': task['created_at'],
                'collab_list_id': task['collab_list_id']
            }
        }), 201
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error creating task: {error_msg}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error creating task: {error_msg}'}), 500

#Get a specific task by ID
@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
@nocache
def get_task(task_id):
    user_id = session.get('user_id')
    task = get_task_by_id(task_id)
    
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    
    # Check access: personal task or collaborative task user has access to
    if task['collab_list_id']:
        from collab_members import is_user_member, is_user_owner
        from collab_lists import get_collab_list_by_id
        
        collab_list = get_collab_list_by_id(task['collab_list_id'])
        if collab_list:
            # Check if user has access (is owner or member)
            if not is_user_owner(task['collab_list_id'], user_id) and not is_user_member(task['collab_list_id'], user_id):
                return jsonify({'success': False, 'message': 'Access denied'}), 403
    else:
        # Personal task - check ownership
        if task['user_id'] != user_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    return jsonify({
        'success': True,
        'task': {
            'id': task['id'],
            'title': task['title'],
            'description': task['description'] or '',
            'priority': task['priority'],
            'status': task['status'],
            'due_date': task['due_date'] or '',
            'created_at': task['created_at'],
            'updated_at': task['updated_at'],
            'collab_list_id': task['collab_list_id']
        }
    })

#Update a task
@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
@nocache
def update_user_task(task_id):
    user_id = session.get('user_id')
    data = request.get_json()
    
    # Check if task exists and user has access
    task = get_task_by_id(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    
    # Check access
    if task['collab_list_id']:
        from collab_members import is_user_member, is_user_owner
        from collab_lists import get_collab_list_by_id
        
        collab_list = get_collab_list_by_id(task['collab_list_id'])
        if collab_list:
            # Check if user has access (is owner or member)
            if not is_user_owner(task['collab_list_id'], user_id) and not is_user_member(task['collab_list_id'], user_id):
                return jsonify({'success': False, 'message': 'Access denied'}), 403
    else:
        if task['user_id'] != user_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Get update fields
    title = data.get('title')
    description = data.get('description')
    priority = data.get('priority')
    status = data.get('status')
    due_date = data.get('due_date')
    
    # Validate title if provided
    if title is not None and not title.strip():
        return jsonify({'success': False, 'message': 'Task title cannot be empty'}), 400
    
    # Convert empty description strings to None
    if description is not None:
        description = description.strip() or None
    
    try:
        updated_task = update_task(
            task_id=task_id,
            user_id=user_id,
            title=title.strip() if title else None,
            description=description,
            priority=priority,
            status=status,
            due_date=due_date if due_date else None
        )
        
        if not updated_task:
            return jsonify({'success': False, 'message': 'No fields to update'}), 400
        
        return jsonify({
            'success': True,
            'message': 'Task updated successfully',
            'task': {
                'id': updated_task['id'],
                'title': updated_task['title'],
                'description': updated_task['description'] or '',
                'priority': updated_task['priority'],
                'status': updated_task['status'],
                'due_date': updated_task['due_date'] or '',
                'updated_at': updated_task['updated_at']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating task: {str(e)}'}), 500

#delete a task
@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
@nocache
def delete_user_task(task_id):
    user_id = session.get('user_id')
    
    # Check if task exists and user has access
    task = get_task_by_id(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    
    # Check access
    if task['collab_list_id']:
        from collab_members import is_user_member, is_user_owner
        from collab_lists import get_collab_list_by_id
        
        collab_list = get_collab_list_by_id(task['collab_list_id'])
        if collab_list:
            # Check if user has access (is owner or member)
            if not is_user_owner(task['collab_list_id'], user_id) and not is_user_member(task['collab_list_id'], user_id):
                return jsonify({'success': False, 'message': 'Access denied'}), 403
    else:
        if task['user_id'] != user_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        deleted = delete_task(task_id, user_id)
        if deleted:
            return jsonify({'success': True, 'message': 'Task deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete task'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting task: {str(e)}'}), 500

#Update only the status of a task
@task_bp.route('/tasks/<int:task_id>/status', methods=['PUT'])
@login_required
@nocache
def update_task_status(task_id):
    user_id = session.get('user_id')
    data = request.get_json()
    
    new_status = data.get('status')
    if not new_status:
        return jsonify({'success': False, 'message': 'Status is required'}), 400
    
    # Check if task exists and user has access
    task = get_task_by_id(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    
    # Check access
    if task['collab_list_id']:
        from collab_members import is_user_member, is_user_owner
        from collab_lists import get_collab_list_by_id
        
        collab_list = get_collab_list_by_id(task['collab_list_id'])
        if collab_list:
            # Check if user has access (is owner or member)
            if not is_user_owner(task['collab_list_id'], user_id) and not is_user_member(task['collab_list_id'], user_id):
                return jsonify({'success': False, 'message': 'Access denied'}), 403
    else:
        if task['user_id'] != user_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        updated_task = update_task(task_id, user_id, status=new_status)
        if updated_task:
            return jsonify({
                'success': True,
                'message': 'Task status updated successfully',
                'task': {
                    'id': updated_task['id'],
                    'status': updated_task['status']
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to update status'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating status: {str(e)}'}), 500

#Archive a task
@task_bp.route('/tasks/<int:task_id>/archive', methods=['POST'])
@login_required
@nocache
def archive_user_task(task_id):
    user_id = session.get('user_id')
    
    # Check if task exists and user has access
    task = get_task_by_id(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    
    # Check access
    if task['collab_list_id']:
        from collab_members import is_user_member, is_user_owner
        from collab_lists import get_collab_list_by_id
        
        collab_list = get_collab_list_by_id(task['collab_list_id'])
        if collab_list:
            # Check if user has access (is owner or member)
            if not is_user_owner(task['collab_list_id'], user_id) and not is_user_member(task['collab_list_id'], user_id):
                return jsonify({'success': False, 'message': 'Access denied'}), 403
    else:
        if task['user_id'] != user_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        archived_task = archive_task(task_id, user_id)
        if archived_task:
            return jsonify({
                'success': True,
                'message': 'Task archived successfully',
                'task': {
                    'id': archived_task['id'],
                    'archived': archived_task['archived']
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to archive task'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error archiving task: {str(e)}'}), 500

#unarchive
@task_bp.route('/tasks/<int:task_id>/unarchive', methods=['POST'])
@login_required
@nocache
def unarchive_user_task(task_id):
    user_id = session.get('user_id')
    
    # Check if task exists and user has access
    task = get_task_by_id(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    
    # Check access
    if task['collab_list_id']:
        from collab_members import is_user_member, is_user_owner
        from collab_lists import get_collab_list_by_id
        
        collab_list = get_collab_list_by_id(task['collab_list_id'])
        if collab_list:
            # Check if user has access (is owner or member)
            if not is_user_owner(task['collab_list_id'], user_id) and not is_user_member(task['collab_list_id'], user_id):
                return jsonify({'success': False, 'message': 'Access denied'}), 403
    else:
        if task['user_id'] != user_id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        unarchived_task = unarchive_task(task_id, user_id)
        if unarchived_task:
            return jsonify({
                'success': True,
                'message': 'Task unarchived successfully',
                'task': {
                    'id': unarchived_task['id'],
                    'archived': unarchived_task['archived']
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to unarchive task'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error unarchiving task: {str(e)}'}), 500

@task_bp.route('/my-tasks')
@login_required
@nocache
def tasks_page():
    return render_template('tasks.html')