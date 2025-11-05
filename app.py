from flask import Flask, render_template
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from routes.auth_routes import auth_bp
from database import initialize_db

app = Flask(__name__)
bcrypt = Bcrypt()
app.secret_key = 'mysupersecretkey'
CORS(app)

initialize_db()

# || REGISTER ROUTES ||
app.register_blueprint(auth_bp, url_prefix='/auth')

# Root route
@app.route('/')
def home():
    return render_template('base.html')

if __name__ == '__main__':
    app.run(debug=True, port=5002)
