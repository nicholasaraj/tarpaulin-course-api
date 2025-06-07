# CS 493
# Nicholas Araj
# Assignment #6
# 06/06/2025
# This is the main.py for Assignment 6 - Tarpaulin Course Management Tool.

from flask import Flask, jsonify
from utils import AuthError
from handlers.users import users_bp
from handlers.courses import courses_bp

# Initialize the Flask application
app = Flask(__name__)

# Register user and course blueprints
app.register_blueprint(users_bp)
app.register_blueprint(courses_bp)

# Root route to verify the service is running
@app.route('/')
def index():
    return jsonify({"message": "Tarpaulin Course Management API is running."}), 200

# Global error handler for AuthError exceptions
@app.errorhandler(AuthError)
def handle_auth_error(e):
    return jsonify({"Error": e.error["description"]}), e.status_code

# Run the app in local development mode
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
