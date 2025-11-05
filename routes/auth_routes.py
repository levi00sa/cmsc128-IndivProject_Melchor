# routes/auth_routes.py
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from flask_bcrypt import Bcrypt
from database import get_db_connection
from functools import wraps
import hashlib
import secrets

auth_bp = Blueprint('auth_bp', __name__)
bcrypt = Bcrypt()

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_bp.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# REGISTER
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('signup.html')
    elif request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        if not all([username, email, password, name]):
            return jsonify({'success': False, 'message': 'All fields are required'})
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Check if username or email already exists
        c.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
        if c.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Username or email already exists'})
        
        # Create new user
        hashed_password = bcrypt.generate_password_hash(password)
        c.execute('INSERT INTO users (username, email, password_hash, name) VALUES (?, ?, ?, ?)',
                  (username, email, hashed_password, name))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        
        session['user_id'] = user_id
        session['username'] = username
        session['name'] = name
        
        return jsonify({'success': True, 'message': 'Account created successfully'})
    
    return render_template('signup.html')


# LOGIN
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['name'] = user['name']
        return jsonify({'success': True, 'message': 'Login successful', 'redirect': '/'}), 200
    else:
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        data = request.get_json()
        new_username = data.get('username')
        new_name = data.get('name')
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get current user data
        c.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
        user = c.fetchone()
        
        # Verify current password if changing password
        if new_password and not bcrypt.check_password_hash(user['password_hash'], current_password):
            conn.close()
            return jsonify({'success': False, 'message': 'Current password is incorrect'})
        
        # Check if new username is already taken
        if new_username != user['username']:
            c.execute('SELECT * FROM users WHERE username = ? AND id != ?', (new_username, session['user_id']))
            if c.fetchone():
                conn.close()
                return jsonify({'success': False, 'message': 'Username already taken'})
        
        # Update user data
        if new_password:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            c.execute('UPDATE users SET username = ?, name = ?, password_hash = ? WHERE id = ?',
                      (new_username, new_name, hashed_password, session['user_id']))
        else:
            c.execute('UPDATE users SET username = ?, name = ? WHERE id = ?',
                      (new_username, new_name, session['user_id']))
        
        conn.commit()
        conn.close()
        
        # Update session
        session['username'] = new_username
        session['name'] = new_name
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    
    # GET request - return user data
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username, email, name FROM users WHERE id = ?', (session['user_id'],))
    user = c.fetchone()
    conn.close()
    
    return render_template('profile.html', user=user)

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        
        if user:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            c.execute('UPDATE users SET reset_token = ?, reset_token_expires = datetime("now", "+1 hour") WHERE id = ?',
                      (reset_token, user[0]))
            conn.commit()
            conn.close()
            # In a real application, send the reset token via email
            # Here, we just return the token for demonstration purposes
            return jsonify({'success': True, 'message': f'Reset token: {reset_token}'})
        else:
            conn.close()
            return jsonify({'success': False, 'message': 'Email not found'})
    
    return render_template('forgot_password.html')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        data = request.get_json()
        new_password = data.get('password')
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE reset_token = ? AND reset_token_expires > datetime("now")', (token,))
        user = c.fetchone()
        
        if user:
            hashed_password = bcrypt.generate_password_hash(new_password)
            c.execute('UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expires = NULL WHERE id = ?',
                      (hashed_password, user[0]))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Password reset successfully'})
        else:
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid or expired token'})
    
    return render_template('reset_password.html', token=token)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth_bp.login'))
