from flask import Flask, render_template, session, redirect, url_for
from flask_cors import CORS
from routes.auth_routes import auth_bp
from routes.task_routes import task_bp
from routes.collab_routes import collab_bp
from database import initialize_db
from tasks import initialize_db as initialize_tasks_db
from collab_lists import initialize_db as initialize_collab_lists_db
from collab_members import initialize_db as initialize_collab_members_db

app = Flask(__name__)
app.secret_key = 'mysupersecretkey'
CORS(app)

initialize_db()
initialize_tasks_db()
initialize_collab_lists_db()
initialize_collab_members_db()

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(task_bp)
app.register_blueprint(collab_bp)

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('task_bp.tasks_page'))
    return render_template('base.html')

if __name__ == '__main__':
    app.run(debug=True, port=5002)
