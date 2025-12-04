from flask import Flask, render_template, session, redirect, url_for, request
from flask_cors import CORS

from extensions import bcrypt
from routes.auth_routes import auth_bp
from routes.task_routes import task_bp
from routes.collab_routes import collab_bp

from database import initialize_db
from tasks import initialize_db as initialize_tasks_db
from collab_lists import initialize_db as initialize_collab_lists_db
from collab_members import initialize_db as initialize_collab_members_db

app = Flask(__name__)
bcrypt.init_app(app)
app.secret_key = 'mysupersecretkey'
CORS(app)

initialize_db()
initialize_tasks_db()
initialize_collab_lists_db()
initialize_collab_members_db()

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(task_bp)
app.register_blueprint(collab_bp)

PROTECTED_PATHS = ('/my-tasks', '/tasks', '/collab_lists', '/auth/logout')


@app.after_request
def add_no_cache_headers(response):
    """Prevent browsers from caching authenticated pages so sessions remain consistent."""
    if session.get('user_id'):
        if any(request.path.startswith(path) for path in PROTECTED_PATHS):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
    return response

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('task_bp.tasks_page'))
    return render_template('base.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
