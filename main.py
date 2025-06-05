from flask import Flask, jsonify
from utils import AuthError
from handlers.users import users_bp
from handlers.courses import courses_bp

app = Flask(__name__)
app.register_blueprint(users_bp)
app.register_blueprint(courses_bp)

@app.errorhandler(AuthError)
def handle_auth_error(e):
    return jsonify({"Error": e.error["description"]}), e.status_code

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
